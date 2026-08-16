import asyncio
import json
import logging
import os
import platform
import socket
import subprocess
import threading
import time
from collections import deque
from pathlib import Path

try:
    import psutil
except Exception:
    psutil = None

logger = logging.getLogger("SATURDAY.Processor")

WOL_MAC_ENV = "SATURDAY_WOL_MAC"
WOL_IP_ENV = "SATURDAY_WOL_IP"
OS_POWER_ENV = "SATURDAY_ENABLE_OS_POWER"
PROFILE_FILE = "device_profile.json"


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name, "true" if default else "false").strip().lower()
    return value in {"1", "true", "yes", "on"}


class DeviceProfile:
    def __init__(self):
        self.hostname = platform.node()
        self.system = platform.system()
        self.machine = platform.machine()
        self.cpu_count = os.cpu_count() or 1
        self.cpu_model = ""
        self.ram_total_gb = 0.0
        self.ram_available_gb = 0.0
        self.disk_total_gb = 0.0
        self.gpu_backends = []
        self.gpu_name = ""
        self.backend = "cpu"
        self.tier = "light"
        self.thread_pool_workers = 4
        self.event_loop = "asyncio"
        self.gc_threshold = 75
        self.memory_warn = 75
        self.memory_critical = 90
        self.cpu_warn = 70
        self.cpu_critical = 90
        self.optimized_at = time.time()

    def _probe_cpu(self):
        if psutil is None:
            return
        try:
            freq = psutil.cpu_freq()
            if freq and freq.max:
                self.cpu_model = f"{self.cpu_count} cores @ {freq.max:.0f} MHz"
            else:
                self.cpu_model = f"{self.cpu_count} cores"
        except Exception:
            self.cpu_model = f"{self.cpu_count} cores"
        try:
            for info in psutil.cpu_freq(percpu=True) or []:
                pass
        except Exception:
            pass

    def _probe_memory(self):
        if psutil is None:
            return
        vm = psutil.virtual_memory()
        self.ram_total_gb = round(vm.total / (1024**3), 1)
        self.ram_available_gb = round(vm.available / (1024**3), 1)

    def _probe_disk(self):
        if psutil is None:
            return
        try:
            du = psutil.disk_usage(os.path.expanduser("~") or "/")
            self.disk_total_gb = round(du.total / (1024**3), 1)
        except Exception:
            try:
                du = psutil.disk_usage("/")
                self.disk_total_gb = round(du.total / (1024**3), 1)
            except Exception:
                pass

    def _probe_gpu(self):
        try:
            import torch
            if torch.cuda.is_available():
                self.gpu_backends.append("cuda")
                self.gpu_name = torch.cuda.get_device_name(0)
        except Exception:
            pass
        try:
            os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
            import tensorflow as tf
            devices = tf.config.list_physical_devices("GPU")
            if devices:
                self.gpu_backends.append("tensorflow-gpu")
                if not self.gpu_name:
                    self.gpu_name = str(devices[0])
        except Exception:
            pass
        try:
            import onnxruntime
            providers = onnxruntime.get_available_providers()
            if "CUDAExecutionProvider" in providers:
                self.gpu_backends.append("onnx-cuda")
        except Exception:
            pass

    def _tune(self):
        logical = self.cpu_count
        self.thread_pool_workers = max(2, min(32, int(logical * 1.5)))
        if self.gpu_backends:
            self.backend = "gpu" if "cuda" in self.gpu_backends else "gpu"
            self.tier = "heavy"
            self.gc_threshold = 85
            self.memory_warn = 80
            self.memory_critical = 92
        elif self.ram_total_gb >= 16 and logical >= 8:
            self.backend = "cpu"
            self.tier = "standard"
            self.gc_threshold = 80
            self.memory_warn = 78
            self.memory_critical = 92
        elif self.ram_total_gb >= 8:
            self.backend = "cpu"
            self.tier = "medium"
            self.thread_pool_workers = max(2, min(16, logical))
            self.gc_threshold = 78
            self.memory_warn = 75
            self.memory_critical = 90
        else:
            self.backend = "cpu"
            self.tier = "light"
            self.thread_pool_workers = max(2, min(8, logical))
            self.gc_threshold = 70
            self.memory_warn = 70
            self.memory_critical = 88
        if self.system == "Windows":
            self.event_loop = "uvloop" if self._uvloop_available() else "asyncio"

    @staticmethod
    def _uvloop_available() -> bool:
        try:
            import uvloop
            return True
        except Exception:
            return False

    def probe(self):
        self._probe_cpu()
        self._probe_memory()
        self._probe_disk()
        self._probe_gpu()
        self._tune()
        self.optimized_at = time.time()
        return self

    def to_dict(self):
        return {
            "hostname": self.hostname,
            "system": self.system,
            "machine": self.machine,
            "cpu_count": self.cpu_count,
            "cpu_model": self.cpu_model,
            "ram_total_gb": self.ram_total_gb,
            "ram_available_gb": self.ram_available_gb,
            "disk_total_gb": self.disk_total_gb,
            "gpu_backends": self.gpu_backends,
            "gpu_name": self.gpu_name,
            "backend": self.backend,
            "tier": self.tier,
            "thread_pool_workers": self.thread_pool_workers,
            "event_loop": self.event_loop,
            "gc_threshold": self.gc_threshold,
            "memory_warn": self.memory_warn,
            "memory_critical": self.memory_critical,
            "cpu_warn": self.cpu_warn,
            "cpu_critical": self.cpu_critical,
            "optimized_at": self.optimized_at,
        }


def optimize_for_device(data_dir: Path) -> DeviceProfile:
    profile = DeviceProfile().probe()
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        target = data_dir / PROFILE_FILE
        existing = {}
        if target.exists():
            try:
                existing = json.loads(target.read_text(encoding="utf-8"))
            except Exception:
                existing = {}
        data = profile.to_dict()
        data.update({"overrides": existing.get("overrides", {})})
        target.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning("Failed to persist device profile: %s", e)
    return profile


def load_device_profile(data_dir: Path) -> dict:
    target = data_dir / PROFILE_FILE
    if target.exists():
        try:
            return json.loads(target.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


class ThreadManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._tasks = {}
        self._counter = 0
        self._max_async_workers = 8

    def track(self, name: str, task, kind: str = "async", priority: int = 5):
        with self._lock:
            self._counter += 1
            self._tasks[name] = {
                "name": name,
                "kind": kind,
                "priority": priority,
                "started": time.time(),
                "task": task,
            }

    def untrack(self, name: str):
        with self._lock:
            self._tasks.pop(name, None)

    def active_count(self) -> int:
        return len(self._tasks)

    def status(self) -> list:
        now = time.time()
        rows = []
        with self._lock:
            for name, entry in list(self._tasks.items()):
                task = entry.get("task")
                state = "running"
                try:
                    if task is not None:
                        if hasattr(task, "done"):
                            state = "done" if task.done() else "running"
                        elif hasattr(task, "is_alive"):
                            state = "alive" if task.is_alive() else "stopped"
                except Exception:
                    state = "unknown"
                rows.append({
                    "name": name,
                    "kind": entry["kind"],
                    "priority": entry["priority"],
                    "state": state,
                    "uptime_sec": int(now - entry["started"]),
                })
        return rows

    def cancel(self, name: str) -> bool:
        with self._lock:
            entry = self._tasks.get(name)
        if not entry:
            return False
        task = entry.get("task")
        if task is not None:
            if hasattr(task, "cancel"):
                try:
                    task.cancel()
                except Exception:
                    pass
            elif hasattr(task, "join"):
                try:
                    task.join(timeout=1.0)
                except Exception:
                    pass
        self.untrack(name)
        return True

    def summary(self) -> dict:
        rows = self.status()
        running = sum(1 for r in rows if r["state"] in ("running", "alive"))
        return {
            "tracked": len(rows),
            "running": running,
            "threads_total": threading.active_count(),
            "tasks": rows,
        }


class PowerManager:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.wol_file = data_dir / "wol.json"
        self.armed = _bool_env(OS_POWER_ENV, default=True)
        self.os = platform.system().lower()
        self._mac = os.getenv(WOL_MAC_ENV, "").strip()
        self._ip = os.getenv(WOL_IP_ENV, "").strip()
        self._loaded = False

    def _load(self):
        if self._loaded:
            return
        self._loaded = True
        if self.wol_file.exists():
            try:
                data = json.loads(self.wol_file.read_text(encoding="utf-8"))
                if not self._mac:
                    self._mac = str(data.get("mac", "")).strip()
                if not self._ip:
                    self._ip = str(data.get("ip", "")).strip()
            except Exception:
                pass
        if not self._mac:
            self._mac = self._detect_mac()

    def _detect_mac(self) -> str:
        if psutil is None:
            return ""
        skip_prefixes = ("00:00:00:00:00:00", "00:50:56", "00:05:69", "52:54:00", "0a:", "ac:de:48")
        candidates = []
        try:
            for iface, addrs in psutil.net_if_addrs().items():
                name = iface.lower()
                if any(v in name for v in ("loopback", "docker", "vethernet", "virtual", "tap", "tun")):
                    continue
                for addr in addrs:
                    if addr.family == psutil.AF_LINK if hasattr(psutil, "AF_LINK") else addr.family.name == "AF_LINK":
                        mac = str(addr.address or "").strip()
                        if not mac or mac.startswith(skip_prefixes):
                            continue
                        candidates.append(mac)
                        break
        except Exception:
            pass
        return candidates[0] if candidates else ""

    def save_wol(self, mac: str = "", ip: str = "", port: int = 9) -> dict:
        self._load()
        if mac:
            self._mac = mac.strip()
        if ip:
            self._ip = ip.strip()
        payload = {"mac": self._mac, "ip": self._ip, "port": int(port)}
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self.wol_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning("Failed to save WoL config: %s", e)
        return self.capabilities()

    @staticmethod
    def _validate_mac(mac: str) -> str:
        cleaned = mac.replace("-", ":").replace(" ", ":").lower()
        parts = cleaned.split(":")
        if len(parts) != 6:
            raise ValueError("MAC must have 6 octets (e.g. AA:BB:CC:DD:EE:FF)")
        octets = []
        for part in parts:
            if len(part) != 2:
                raise ValueError(f"Invalid MAC octet: {part}")
            octets.append(int(part, 16))
        return ":".join(f"{o:02x}" for o in octets)

    def send_wake_on_lan(self, mac: str = "", ip: str = "", port: int = 9) -> dict:
        self._load()
        mac = (mac or self._mac or "").strip()
        if not mac:
            return {"success": False, "error": "No MAC address configured. Provide one or set SATURDAY_WOL_MAC."}
        try:
            mac = self._validate_mac(mac)
        except ValueError as e:
            return {"success": False, "error": str(e)}
        mac_bytes = bytes(int(o, 16) for o in mac.split(":"))
        magic = b"\xff" * 6 + mac_bytes * 16
        targets = [self._ip] if self._ip else []
        targets.append(ip if ip else "255.255.255.255")
        sent = []
        for host in dict.fromkeys(t for t in targets if t):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                    sock.settimeout(1.0)
                    sock.sendto(magic, (host, int(port)))
                sent.append(host)
            except Exception as e:
                logger.warning("WoL send to %s failed: %s", host, e)
        ok = len(sent) > 0
        self.save_wol(mac=mac, ip=self._ip, port=port)
        return {
            "success": ok,
            "mac": mac,
            "targets": sent,
            "port": int(port),
            "message": f"Wake-on-LAN magic packet sent to {mac} via {', '.join(sent)}." if ok else "Wake-on-LAN packet failed.",
        }

    def _os_supported(self) -> bool:
        return self.os in ("windows", "linux", "darwin")

    def os_shutdown(self, delay: int = 0, confirm: bool = False) -> dict:
        if not self.armed:
            return {"success": False, "error": "OS power controls are disabled (SATURDAY_ENABLE_OS_POWER=false)."}
        if not confirm:
            return {"success": False, "error": "Confirmation required."}
        if not self._os_supported():
            return {"success": False, "error": f"OS shutdown not supported on {self.os}."}
        if self.os == "windows":
            cmd = ["shutdown", "/s", "/t", str(max(0, int(delay)))]
        elif self.os == "linux":
            cmd = ["systemctl", "poweroff"]
        else:
            cmd = ["osascript", "-e", "tell application \"System Events\" to shut down"]
        return self._run(cmd, "shutdown")

    def os_restart(self, delay: int = 0, confirm: bool = False) -> dict:
        if not self.armed:
            return {"success": False, "error": "OS power controls are disabled (SATURDAY_ENABLE_OS_POWER=false)."}
        if not confirm:
            return {"success": False, "error": "Confirmation required."}
        if not self._os_supported():
            return {"success": False, "error": f"OS restart not supported on {self.os}."}
        if self.os == "windows":
            cmd = ["shutdown", "/r", "/t", str(max(0, int(delay)))]
        elif self.os == "linux":
            cmd = ["systemctl", "reboot"]
        else:
            cmd = ["osascript", "-e", "tell application \"System Events\" to restart"]
        return self._run(cmd, "restart")

    def os_sleep(self, confirm: bool = False) -> dict:
        if not self.armed:
            return {"success": False, "error": "OS power controls are disabled (SATURDAY_ENABLE_OS_POWER=false)."}
        if not confirm:
            return {"success": False, "error": "Confirmation required."}
        if not self._os_supported():
            return {"success": False, "error": f"OS sleep not supported on {self.os}."}
        if self.os == "windows":
            cmd = ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"]
        elif self.os == "linux":
            cmd = ["systemctl", "suspend"]
        else:
            cmd = ["osascript", "-e", "tell application \"System Events\" to sleep"]
        return self._run(cmd, "sleep")

    def _run(self, cmd, action):
        logger.warning("SATURDAY issuing OS %s command: %s", action, " ".join(cmd))
        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return {"success": True, "action": action, "command": " ".join(cmd)}
        except Exception as e:
            logger.error("OS %s command failed: %s", action, e)
            return {"success": False, "action": action, "error": str(e)}

    def capabilities(self) -> dict:
        self._load()
        return {
            "armed": self.armed,
            "os": self.os,
            "wol_mac": self._mac,
            "wol_ip": self._ip,
            "os_shutdown_supported": self._os_supported(),
            "os_restart_supported": self._os_supported(),
            "os_sleep_supported": self._os_supported(),
            "wol_ready": bool(self._mac),
        }


class RealtimeSearch:
    def __init__(self, event_bus, service=None):
        self.event_bus = event_bus
        self.service = service
        self.recent = deque(maxlen=12)
        self.lock = threading.Lock()
        self._executor = None

    def _get_executor(self):
        if self._executor is None:
            import concurrent.futures
            self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="Search")
        return self._executor

    def search(self, query: str, max_results: int = 6) -> dict:
        query = (query or "").strip()
        if not query:
            return {"success": False, "error": "query is required"}
        with self.lock:
            cache = [r for r in self.recent if r.get("query", "").lower() == query.lower()]
        if cache:
            return {"success": True, "cached": True, **cache[0]}
        future = self._get_executor().submit(self._run_search, query, max_results)
        return {"success": True, "pending": True, "query": query}

    def _run_search(self, query: str, max_results: int) -> dict:
        results = []
        engine = "duckduckgo"
        try:
            if self.service is not None:
                results = self.service.search(query, max_results=max_results) or []
            else:
                results = self._ddg_search(query, max_results)
        except Exception as e:
            logger.error("Realtime search failed for %r: %s", query, e)
            results = []
        payload = {
            "query": query,
            "engine": engine,
            "results": results,
            "timestamp": time.time(),
        }
        with self.lock:
            self.recent.appendleft(payload)
        try:
            self.event_bus.publish("search_results", {"query": query, "results": results, "timestamp": time.time()})
        except Exception:
            pass
        return payload

    @staticmethod
    def _ddg_search(query: str, max_results: int) -> list:
        try:
            import requests
            resp = requests.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
                timeout=6,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            data = {}
        results = []
        for item in data.get("RelatedTopics", []):
            if isinstance(item, dict) and "Text" in item and "FirstURL" in item:
                results.append({
                    "title": str(item.get("Text")).split(" - ")[0],
                    "snippet": item.get("Text"),
                    "url": item.get("FirstURL"),
                })
                if len(results) >= max_results:
                    break
        if not results and data.get("AbstractText"):
            results.append({
                "title": data.get("Heading") or query,
                "snippet": data.get("AbstractText"),
                "url": data.get("AbstractURL") or "",
            })
        if not results:
            results = RealtimeSearch._bing_search(query, max_results)
        if not results:
            results = RealtimeSearch._ddg_html_fallback(query, max_results)
        return results

    @staticmethod
    def _bing_search(query: str, max_results: int) -> list:
        import base64
        import re
        try:
            import requests
            resp = requests.get(
                "https://www.bing.com/search",
                params={"q": query},
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"},
                timeout=8,
            )
            resp.raise_for_status()
            html = resp.text
        except Exception:
            return []
        results = []
        blocks = re.findall(r'<li class="b_algo".*?</li>', html, re.S)
        for block in blocks[:max_results]:
            a = re.search(r'<h2.*?<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', block, re.S)
            if not a:
                continue
            href = a.group(1).replace("&amp;", "&")
            url = href
            m = re.search(r"[?&]u=a1([^&]+)", href)
            if m:
                try:
                    url = base64.b64decode(m.group(1).replace("%3D", "=") + "==").decode("utf-8", "ignore")
                except Exception:
                    url = href
            title = re.sub(r"<[^>]+>", "", a.group(2)).strip()
            sn = re.search(r"<p[^>]*>(.*?)</p>", block, re.S)
            snippet = re.sub(r"<[^>]+>", "", sn.group(1)).strip() if sn else ""
            if title:
                results.append({"title": title, "snippet": snippet, "url": url})
        return results

    @staticmethod
    def _ddg_html_fallback(query: str, max_results: int) -> list:
        import re
        try:
            import requests
            resp = requests.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                headers={"User-Agent": "Mozilla/5.0 SATURDAY-Search/1.0"},
                timeout=8,
            )
            resp.raise_for_status()
            html = resp.text
        except Exception:
            return []
        results = []
        blocks = re.findall(r'class="result__body".*?</div>', html, re.S)
        if not blocks:
            blocks = re.findall(r'class="result".*?</div>', html, re.S)
        for block in blocks[:max_results]:
            a = re.search(r'href="([^"]+)"[^>]*class="result__a"[^>]*>(.*?)</a>', block, re.S)
            snippet = re.search(r'class="result__snippet"[^>]*>(.*?)</a>', block, re.S)
            if not a:
                continue
            url = a.group(1)
            if url.startswith("//"):
                url = "https:" + url
            title = re.sub(r"<[^>]+>", "", a.group(2)).strip()
            results.append({
                "title": title,
                "snippet": re.sub(r"<[^>]+>", "", snippet.group(1)).strip() if snippet else "",
                "url": url,
            })
        return results

    def recent_queries(self) -> list:
        with self.lock:
            return list(self.recent)


class SaturdayProcessor:
    def __init__(self, event_bus=None, data_dir: Path | None = None):
        self.event_bus = event_bus
        self.data_dir = data_dir or Path("data")
        self.profile = None
        self.threads = ThreadManager()
        self.power = PowerManager(self.data_dir)
        self.search = RealtimeSearch(event_bus)
        self.brain = None
        self.mode = "performance"
        self.last_activity = time.time()
        self.autonomous_loop_task = None
        self._loop = None
        self.activity = deque(maxlen=60)

    def set_brain(self, brain):
        self.brain = brain

    def set_activity(self, message: str):
        entry = {"ts": time.time(), "message": message}
        self.activity.appendleft(entry)
        if self.event_bus is not None:
            try:
                self.event_bus.publish("processor_activity", entry)
            except Exception:
                pass

    def optimize(self, save: bool = True) -> dict:
        profile = optimize_for_device(self.data_dir) if save else DeviceProfile().probe()
        self.profile = profile
        self.set_activity(f"Device optimization complete: tier={profile.tier}, backend={profile.backend}, threads={profile.thread_pool_workers}")
        if self.event_bus is not None:
            try:
                self.event_bus.publish("device_profile", profile.to_dict())
            except Exception:
                pass
        return profile.to_dict()

    def start_loops(self, loop=None):
        self._loop = loop or asyncio.get_event_loop()
        if self.autonomous_loop_task is None or self.autonomous_loop_task.done():
            self.autonomous_loop_task = self._loop.create_task(self.autonomous_loop())
            self.threads.track("processor.autonomous", self.autonomous_loop_task, kind="async", priority=1)

    def _reset_idle(self):
        self.last_activity = time.time()

    async def autonomous_loop(self):
        cycle = 0
        while True:
            try:
                cycle += 1
                await asyncio.sleep(15)
                if psutil is None:
                    continue
                cpu = psutil.cpu_percent(interval=None)
                ram = psutil.virtual_memory().percent
                idle_sec = time.time() - self.last_activity
                if cpu > (self.profile.cpu_critical if self.profile else 90) and self.mode != "performance":
                    self.mode = "performance"
                    self.set_activity(f"Autonomous optimization: high load ({cpu:.0f}%) -> performance mode")
                    if self.event_bus is not None:
                        self.event_bus.publish("power_mode", {"mode": "performance", "source": "processor"})
                elif cpu < 30 and ram < 60 and idle_sec > 240 and self.mode != "low":
                    self.mode = "low"
                    self.set_activity(f"Autonomous optimization: idle {int(idle_sec)}s -> low-power mode")
                    if self.event_bus is not None:
                        self.event_bus.publish("power_mode", {"mode": "low", "source": "processor"})
                elif self.mode == "low" and (cpu > 45 or idle_sec < 60):
                    self.mode = "performance"
                    self.set_activity("Autonomous optimization: re-engaged -> performance mode")
                    if self.event_bus is not None:
                        self.event_bus.publish("power_mode", {"mode": "performance", "source": "processor"})
                if cycle % 12 == 0:
                    self.set_activity(
                        f"Processor heartbeat: cpu={cpu:.0f}%, ram={ram:.0f}%, mode={self.mode}, threads={self.threads.active_count()}"
                    )
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug("Autonomous loop iteration error: %s", e)

    async def think(self, goal: str = "") -> dict:
        goal = (goal or "").strip() or "observe and optimize the system"
        if self.brain is not None:
            try:
                if hasattr(self.brain, "think"):
                    thought = self.brain.think(goal)
                    self.set_activity(f"Brain thought: {goal}")
                    return {"brain": "linked", "goal": goal, "response": thought}
            except Exception as e:
                logger.warning("Brain think failed: %s", e)
        heuristic = f"SATURDAY is observing the system with tier '{self.profile.tier if self.profile else 'unknown'}' on backend '{self.profile.backend if self.profile else 'cpu'}'. "
        if self.mode == "low":
            heuristic += "Currently conserving power while idle."
        else:
            heuristic += "Monitoring resource usage, security, and user presence."
        self.set_activity(f"Brain thought: {goal}")
        return {"brain": "internal", "goal": goal, "response": heuristic}

    def status(self) -> dict:
        return {
            "processor": "SATURDAY Processor v1.0",
            "uptime_sec": int(time.time() - (self.profile.optimized_at if self.profile else time.time())),
            "mode": self.mode,
            "profile": self.profile.to_dict() if self.profile else {},
            "threads": self.threads.summary(),
            "power": self.power.capabilities(),
            "search_recent": self.search.recent_queries(),
            "activity": list(self.activity),
            "brain_connected": self.brain is not None,
        }
