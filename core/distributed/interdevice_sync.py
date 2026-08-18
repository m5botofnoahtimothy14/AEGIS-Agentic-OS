import structlog
import time
import json
import os
import hashlib
import threading
from datetime import datetime

logger = structlog.get_logger("SATURDAY.Distributed.Sync")

SYNC_STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "mesh_sync_state.json")


class InterDeviceSync:
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.event_bus.subscribe("mesh_update", self.sync_mesh_state)
        self.event_bus.subscribe("device_discovered", self._on_device_discovered)
        self.event_bus.subscribe("device_left", self._on_device_left)

        self.known_devices = {}
        self.mesh_topology = {}
        self.sync_history = []
        self.local_node_id = self._generate_node_id()
        self.local_state = {}
        self._conflict_log = []
        self._max_sync_history = 200
        self._sync_interval = 30
        self._thread = None
        self._running = False

        self._load_state()
        logger.info("InterDeviceSync initialized", local_node=self.local_node_id)

    def _generate_node_id(self):
        try:
            import platform
            raw = platform.node() + str(os.getpid()) + str(time.time())
            return hashlib.sha256(raw.encode()).hexdigest()[:12]
        except Exception:
            return hashlib.sha256(str(time.time()).encode()).hexdigest()[:12]

    def _load_state(self):
        try:
            if os.path.exists(SYNC_STATE_FILE):
                with open(SYNC_STATE_FILE, "r") as f:
                    data = json.load(f)
                    self.known_devices = data.get("devices", {})
                    self.mesh_topology = data.get("topology", {})
        except Exception:
            pass

    def _save_state(self):
        try:
            os.makedirs(os.path.dirname(SYNC_STATE_FILE), exist_ok=True)
            with open(SYNC_STATE_FILE, "w") as f:
                json.dump({
                    "devices": self.known_devices,
                    "topology": self.mesh_topology,
                    "last_sync": time.time(),
                    "local_node": self.local_node_id,
                }, f, indent=2, default=str)
        except Exception:
            pass

    def start_sync_loop(self):
        self._running = True
        self._thread = threading.Thread(target=self._sync_loop, daemon=True)
        self._thread.start()
        logger.info("Mesh sync loop started")

    def stop_sync_loop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _sync_loop(self):
        while self._running:
            try:
                self._broadcast_heartbeat()
                self._check_stale_devices()
            except Exception as e:
                logger.warning("Sync loop error: %s", e)
            time.sleep(self._sync_interval)

    def _broadcast_heartbeat(self):
        heartbeat = {
            "node_id": self.local_node_id,
            "type": "heartbeat",
            "timestamp": time.time(),
            "state_hash": self._compute_state_hash(),
            "device_count": len(self.known_devices),
        }
        if self.event_bus:
            self.event_bus.publish("mesh_heartbeat", heartbeat)

    def _compute_state_hash(self):
        state_str = json.dumps(self.local_state, sort_keys=True, default=str)
        return hashlib.md5(state_str.encode()).hexdigest()[:8]

    def _check_stale_devices(self):
        now = time.time()
        stale_threshold = 120
        stale_nodes = []
        for node_id, device in list(self.known_devices.items()):
            last_seen = device.get("last_seen", 0)
            if now - last_seen > stale_threshold:
                stale_nodes.append(node_id)
        for node_id in stale_nodes:
            self.known_devices[node_id]["status"] = "stale"
            logger.info("Device marked stale: %s", node_id)
        if stale_nodes:
            self._save_state()

    def _on_device_discovered(self, data):
        if not isinstance(data, dict):
            return
        node_id = data.get("node_id")
        if not node_id:
            return
        self.known_devices[node_id] = {
            "node_id": node_id,
            "name": data.get("name", "Unknown Device"),
            "type": data.get("type", "unknown"),
            "ip": data.get("ip", ""),
            "capabilities": data.get("capabilities", []),
            "status": "active",
            "last_seen": time.time(),
            "discovered_at": self.known_devices.get(node_id, {}).get("discovered_at", time.time()),
        }
        self._update_topology()
        self._save_state()
        if self.event_bus:
            self.event_bus.publish("mesh_device_added", {"node_id": node_id, "device": self.known_devices[node_id]})

    def _on_device_left(self, data):
        if not isinstance(data, dict):
            return
        node_id = data.get("node_id")
        if node_id in self.known_devices:
            self.known_devices[node_id]["status"] = "left"
            self.known_devices[node_id]["last_seen"] = time.time()
            self._update_topology()
            self._save_state()

    def _update_topology(self):
        active = {nid: d for nid, d in self.known_devices.items() if d.get("status") == "active"}
        self.mesh_topology = {
            "node_count": len(active) + 1,
            "nodes": list(active.keys()) + [self.local_node_id],
            "last_updated": time.time(),
        }

    async def sync_mesh_state(self, data: dict):
        incoming_devices = data.get("devices", {})
        incoming_topology = data.get("topology", {})
        incoming_state = data.get("state", {})
        incoming_node = data.get("source_node", "unknown")

        logger.info("Synchronizing mesh state", node_count=data.get("total_devices", len(incoming_devices)))

        conflicts = self._merge_device_lists(incoming_devices)
        if conflicts:
            self._conflict_log.extend(conflicts)
            self._conflict_log = self._conflict_log[-100:]

        self._merge_state(incoming_state)
        self._update_topology()
        self._save_state()

        sync_record = {
            "timestamp": time.time(),
            "source_node": incoming_node,
            "devices_merged": len(incoming_devices),
            "conflicts": len(conflicts),
            "local_devices": len(self.known_devices),
        }
        self.sync_history.append(sync_record)
        if len(self.sync_history) > self._max_sync_history:
            self.sync_history = self.sync_history[-self._max_sync_history:]

        self.event_bus.publish("sync_complete", {
            "timestamp": time.time(),
            "devices": len(self.known_devices),
            "conflicts_resolved": len(conflicts),
        })

        return sync_record

    def _merge_device_lists(self, incoming_devices):
        conflicts = []
        for node_id, incoming in incoming_devices.items():
            if node_id == self.local_node_id:
                continue
            existing = self.known_devices.get(node_id)
            if existing is None:
                self.known_devices[node_id] = incoming
                self.known_devices[node_id]["last_seen"] = time.time()
            else:
                incoming_ts = incoming.get("last_seen", 0)
                existing_ts = existing.get("last_seen", 0)
                if incoming_ts > existing_ts:
                    conflicts.append({
                        "node_id": node_id,
                        "resolution": "incoming_wins",
                        "timestamp": time.time(),
                    })
                    self.known_devices[node_id].update(incoming)
                    self.known_devices[node_id]["last_seen"] = time.time()
                else:
                    conflicts.append({
                        "node_id": node_id,
                        "resolution": "local_wins",
                        "timestamp": time.time(),
                    })
        return conflicts

    def _merge_state(self, incoming_state):
        for key, value in incoming_state.items():
            if key not in self.local_state:
                self.local_state[key] = value

    def get_mesh_status(self):
        active = {nid: d for nid, d in self.known_devices.items() if d.get("status") == "active"}
        return {
            "local_node": self.local_node_id,
            "total_devices": len(self.known_devices),
            "active_devices": len(active),
            "devices": self.known_devices,
            "topology": self.mesh_topology,
            "recent_syncs": self.sync_history[-10:],
            "conflicts": self._conflict_log[-10:],
        }

    def get_device(self, node_id: str):
        return self.known_devices.get(node_id)

    def remove_device(self, node_id: str):
        if node_id in self.known_devices:
            del self.known_devices[node_id]
            self._update_topology()
            self._save_state()
            return True
        return False

    def update_local_state(self, state: dict):
        self.local_state.update(state)
        self._save_state()
