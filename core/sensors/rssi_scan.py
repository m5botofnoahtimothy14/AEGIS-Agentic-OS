                      
import logging
from core.event_bus import EventBus

logger = logging.getLogger("SATURDAY.Sensors.RSSI")

class RSSIScanner:
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        logger.info("RSSI Proximity Scanner initialized.")

    async def scan_proximity(self):
        logger.debug("Scanning for device proximity signals...")
        signals = self._collect_rssi()
        if signals:
            self.event_bus.publish("proximity_scan", {"signals": signals})
            logger.info("Proximity scan completed", devices=len(signals))
        return signals

    def _collect_rssi(self) -> list:
        signals = []
        try:
            import subprocess
            system = None
            import platform
            system = platform.system()
            if system == "Darwin":
                result = subprocess.run(
                    ["/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport", "-s"],
                    capture_output=True, text=True, timeout=5,
                )
                for line in result.stdout.splitlines()[1:]:
                    parts = line.split()
                    if len(parts) >= 4:
                        try:
                            signals.append({"ssid": " ".join(parts[:-3]), "rssi": int(parts[-3]), "bssid": parts[0]})
                        except ValueError:
                            continue
            elif system == "Windows":
                result = subprocess.run(["netsh", "wlan", "show", "networks", "mode=bssid"],
                                        capture_output=True, text=True, timeout=5)
                ssid, rssi = None, None
                for line in result.stdout.splitlines():
                    if "SSID" in line and "BSSID" not in line:
                        ssid = line.split(":", 1)[-1].strip()
                    if "Signal" in line:
                        try:
                            rssi = int("".join(c for c in line.split(":", 1)[-1] if c.isdigit()) or 0)
                        except ValueError:
                            rssi = 0
                        if ssid:
                            signals.append({"ssid": ssid, "rssi": rssi})
                            ssid = None
            else:
                try:
                    import wifi
                    for cell in wifi.Cell.all("wlan0"):
                        signals.append({"ssid": cell.ssid, "rssi": cell.signal})
                except Exception:
                    logger.debug("No wifi scan module available on Linux")
        except Exception as e:
            logger.debug("RSSI scan failed", error=str(e))
        return signals
