import logging
import threading
import time
import psutil
import structlog

logger = structlog.get_logger("SATURDAY.CyberDefense")

class CyberDefense:
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.active = False
        self.threat_score = 0.0
        self.monitoring = False
        self.event_bus.subscribe("security_alert", self.handle_alert)
        self._suspicious_patterns = [
            "unusual_network",
            "brute_force",
            "privilege_escalation",
            "data_exfiltration",
            "malware_activity",
        ]

    def activate(self):
        self.active = True
        self.monitoring = True
        threading.Thread(target=self._active_monitor, daemon=True).start()
        logger.info("Cyber defense activated.")

    def deactivate(self):
        self.active = False
        self.monitoring = False
        logger.info("Cyber defense deactivated.")

    def _active_monitor(self):
        while self.active:
            try:
                self._scan_system()
                time.sleep(5)
            except Exception as e:
                logger.warning("Cyber defense monitor error", error=str(e))
                time.sleep(10)

    def _scan_system(self):
        threats = []
        try:
            # CPU spike detection
            cpu_percent = psutil.cpu_percent(interval=0.5)
            if cpu_percent > 90:
                threats.append({"type": "cpu_spike", "value": cpu_percent, "severity": "high"})

            # Process scanning for suspicious behavior
            for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
                try:
                    pinfo = proc.info
                    if pinfo["cpu_percent"] > 80 and pinfo["name"].lower() not in ["system", "idle", "svchost"]:
                        threats.append({"type": "high_cpu_process", "pid": pinfo["pid"], "name": pinfo["name"], "value": pinfo["cpu_percent"]})
                    if pinfo["memory_percent"] > 90:
                        threats.append({"type": "high_memory_process", "pid": pinfo["pid"], "name": pinfo["name"], "value": pinfo["memory_percent"]})
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass

            # Network connection scanning for unusual activity
            network_threats = self._scan_network()
            threats.extend(network_threats)

            if threats:
                self.threat_score = min(100.0, self.threat_score + 5.0)
                self.event_bus.publish("security_alert", {
                    "type": "system_scan",
                    "threats": threats,
                    "threat_score": self.threat_score,
                    "source": "cyber_defense",
                })
        except Exception as e:
            logger.warning("System scan error", error=str(e))

    def _scan_network(self):
        threats = []
        try:
            connections = psutil.net_connections(kind="inet")
            for conn in connections:
                if conn.status == "ESTABLISHED":
                    laddr = f"{conn.laddr.ip}:{conn.laddr.port}"
                    # Check for connections to unusual ports or external IPs
                    if conn.raddr:
                        raddr = f"{conn.raddr.ip}:{conn.raddr.port}"
                        # Flag international connections as potentially suspicious
                        if conn.raddr.ip.startswith(("10.", "192.168.", "172.")):
                            pass  # Internal, OK
                        elif conn.raddr.port in [22, 23, 3389, 4444, 4445, 6667, 1337]:
                            threats.append({"type": "suspicious_port", "detail": f"Connection to {raddr} on port {conn.raddr.port}"})
        except Exception:
            pass
        return threats

    def handle_alert(self, data):
        msg = data.get("message", "") or str(data)
        self.threat_score = min(100.0, self.threat_score + 3.0)
        logger.warning("Cyber defense alert handled", message=msg, threat_score=self.threat_score)
        self.event_bus.publish("cooldown", {
            "action": "cyber_defense_alert",
            "threat_score": self.threat_score,
            "message": msg,
        })

    def get_status(self):
        return {
            "active": self.active,
            "threat_score": round(self.threat_score, 1),
            "monitoring": self.monitoring,
        }