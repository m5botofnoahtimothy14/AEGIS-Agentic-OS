import logging
import threading
import time
import json
import os
import math
from datetime import datetime

logger = logging.getLogger("SATURDAY.Health.SensorHub")

SENSOR_DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "sensor_data.json")


class SensorHub:
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.active = False
        self.sensors = {}
        self.latest_readings = {}
        self.reading_history = []
        self._max_history = 500
        self._poll_interval = 2.0
        self._thread = None

    def start_polling(self):
        self.active = True
        self._discover_sensors()
        self._thread = threading.Thread(target=self._hub_loop, daemon=True)
        self._thread.start()
        logger.info("SensorHub polling started with %d sensors", len(self.sensors))

    def stop_polling(self):
        self.active = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("SensorHub polling stopped")

    def _discover_sensors(self):
        self.sensors = {}

        try:
            import psutil
            self.sensors["cpu_temp"] = self._read_cpu_temp
            self.sensors["battery"] = self._read_battery
            self.sensors["cpu_usage"] = self._read_cpu_usage
            self.sensors["memory_usage"] = self._read_memory_usage
            self.sensors["disk_io"] = self._read_disk_io
            self.sensors["network_io"] = self._read_network_io
            self.sensors["process_count"] = self._read_process_count
        except ImportError:
            logger.warning("psutil not available, limited sensors")

        self.sensors["timestamp"] = self._read_timestamp
        self.sensors["uptime"] = self._read_uptime

    def _hub_loop(self):
        while self.active:
            try:
                self._poll_all_sensors()
                self._publish_readings()
                self._check_alerts()
                self._save_data()
            except Exception as e:
                logger.warning("SensorHub poll error: %s", e)
            time.sleep(self._poll_interval)

    def _poll_all_sensors(self):
        readings = {}
        for sensor_name, reader_fn in self.sensors.items():
            try:
                readings[sensor_name] = reader_fn()
            except Exception as e:
                readings[sensor_name] = {"error": str(e), "value": None}
        self.latest_readings = readings
        self.reading_history.append({
            "timestamp": time.time(),
            "readings": readings,
        })
        if len(self.reading_history) > self._max_history:
            self.reading_history = self.reading_history[-self._max_history:]

    def _publish_readings(self):
        if self.event_bus:
            self.event_bus.publish("sensor_data", self.latest_readings)
            self.event_bus.publish("vitals_update", {
                "type": "cpu_usage",
                "value": self.latest_readings.get("cpu_usage", {}).get("value", 0),
            })
            battery = self.latest_readings.get("battery", {})
            if battery and battery.get("value") is not None:
                self.event_bus.publish("vitals_update", {
                    "type": "battery",
                    "value": battery.get("value"),
                    "percent": battery.get("percent", 0),
                })

    def _check_alerts(self):
        if not self.event_bus:
            return
        cpu = self.latest_readings.get("cpu_usage", {})
        if isinstance(cpu, dict) and cpu.get("value") and cpu["value"] > 90:
            self.event_bus.publish("system_alert", {
                "type": "high_cpu",
                "value": cpu["value"],
                "source": "sensor_hub",
            })
        mem = self.latest_readings.get("memory_usage", {})
        if isinstance(mem, dict) and mem.get("percent") and mem["percent"] > 90:
            self.event_bus.publish("system_alert", {
                "type": "high_memory",
                "value": mem["percent"],
                "source": "sensor_hub",
            })
        battery = self.latest_readings.get("battery", {})
        if isinstance(battery, dict) and battery.get("percent") and battery["percent"] < 15 and battery.get("plugged") is False:
            self.event_bus.publish("system_alert", {
                "type": "low_battery",
                "value": battery["percent"],
                "source": "sensor_hub",
            })

    def _save_data(self):
        try:
            os.makedirs(os.path.dirname(SENSOR_DATA_FILE), exist_ok=True)
            data = {
                "latest": self.latest_readings,
                "history_count": len(self.reading_history),
                "last_updated": time.time(),
            }
            with open(SENSOR_DATA_FILE, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception:
            pass

    def _read_cpu_temp(self):
        try:
            import psutil
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    if entries:
                        return {"value": entries[0].current, "unit": "C", "sensor": name}
        except Exception:
            pass
        return {"value": None, "unit": "C", "sensor": "unavailable"}

    def _read_battery(self):
        try:
            import psutil
            bat = psutil.sensors_battery()
            if bat:
                return {"value": 1 if bat.power_plugged else 0, "percent": bat.percent, "plugged": bat.power_plugged, "secs_left": bat.secsleft}
        except Exception:
            pass
        return {"value": None, "percent": 0, "plugged": True}

    def _read_cpu_usage(self):
        import psutil
        return {"value": psutil.cpu_percent(interval=0.1), "cores": psutil.cpu_count()}

    def _read_memory_usage(self):
        import psutil
        mem = psutil.virtual_memory()
        return {"value": mem.used, "percent": mem.percent, "total_mb": round(mem.total / (1024 * 1024), 1), "available_mb": round(mem.available / (1024 * 1024), 1)}

    def _read_disk_io(self):
        import psutil
        io = psutil.disk_io_counters()
        if io:
            return {"read_mb": round(io.read_bytes / (1024 * 1024), 1), "write_mb": round(io.write_bytes / (1024 * 1024), 1)}
        return {"read_mb": 0, "write_mb": 0}

    def _read_network_io(self):
        import psutil
        net = psutil.net_io_counters()
        return {"sent_mb": round(net.bytes_sent / (1024 * 1024), 1), "recv_mb": round(net.bytes_recv / (1024 * 1024), 1), "packets_sent": net.packets_sent, "packets_recv": net.packets_recv}

    def _read_process_count(self):
        import psutil
        return {"value": len(list(psutil.process_iter()))}

    def _read_timestamp(self):
        return {"value": datetime.now().isoformat()}

    def _read_uptime(self):
        import psutil
        return {"value": round(time.time() - psutil.boot_time(), 0)}

    def get_latest(self):
        return self.latest_readings

    def get_history(self, limit=50):
        return self.reading_history[-limit:]

    def get_health_summary(self):
        readings = self.latest_readings
        return {
            "cpu_percent": readings.get("cpu_usage", {}).get("value", 0),
            "memory_percent": readings.get("memory_usage", {}).get("percent", 0),
            "battery_percent": readings.get("battery", {}).get("percent", 0),
            "battery_plugged": readings.get("battery", {}).get("plugged", True),
            "disk_read_mb": readings.get("disk_io", {}).get("read_mb", 0),
            "disk_write_mb": readings.get("disk_io", {}).get("write_mb", 0),
            "network_sent_mb": readings.get("network_io", {}).get("sent_mb", 0),
            "network_recv_mb": readings.get("network_io", {}).get("recv_mb", 0),
            "process_count": readings.get("process_count", {}).get("value", 0),
            "uptime_seconds": readings.get("uptime", {}).get("value", 0),
        }
