                    
import logging
import platform

logger = logging.getLogger("SATURDAY.HomeBot.Control")

class HomeBotBridgeSensors:
    def read_ultrasonic(self): return 0
    def read_vibration(self): return 0
    def scan_wifi_heatmap(self): return []

class HomeBotBridgeNav:
    def __init__(self):
        self.position = [0, 0]
        self.grid_map = []
    def move_to(self, target, bot):
        current = list(self.position)
        target = list(target)
        self.grid_map.append({"from": current, "to": target})
        self.position = target
        if bot and hasattr(bot, "motors"):
            try:
                dx = target[0] - current[0]
                dy = target[1] - current[1]
                steps = max(1, int(abs(dx) + abs(dy)))
                bot.motors.move(x=dx, y=dy, duration=steps)
            except Exception as e:
                logger.warning("Bridge motor move failed", error=str(e))
        logger.info("HomeBot bridge navigation updated", target=target, position=self.position)
        return {"position": self.position, "steps": self.grid_map}

class HomeBot:
    def __init__(self):
        self.os_type = platform.system()
        if self.os_type == "Windows":
            logger.info("Initializing HomeBot Bridge (Windows Mode)")
            self.sensors = HomeBotBridgeSensors()
            self.navigation = HomeBotBridgeNav()
            self.connected = False
            self._try_connect()
        else:
                              
            from homebot.motors import OmniMotors
            from homebot.navigation import Navigation
            from homebot.sensors import Sensors
            self.sensors = Sensors()
            self.motors = OmniMotors()
            self.navigation = Navigation(self.sensors)
            self.connected = True

    def _try_connect(self):
        try:
            import serial              
            logger.warning("HomeBot direct bridge is not configured on Windows. Use core.homebot_integration for real transport.")
        except Exception as e:
            logger.warning(f"Could not establish serial connection to HomeBot: {e}")

    def execute_command(self, command, duration=1, speed=80):
        logger.info(f"Executing HomeBot command: {command}")
        if self.os_type == "Windows":
            if self.connected:
                print(f"[BRIDGE] Sending to M5Stack: {command}")
            else:
                logger.error("Cannot execute command: HomeBot not connected.")
        else:
            if not hasattr(self, "motors"):
                logger.error("Cannot execute command: HomeBot motors unavailable.")
                return
            direction = command.lower()
            self.motors.move(direction, duration=duration, speed=speed)

    def autonomous_navigation(self, target):
        logger.info(f"Autonomous navigation to {target} requested.")
        if self.os_type == "Windows":
            print(f"[BRIDGE] Requesting autonomous nav to {target}")
        else:
            self.navigation.navigate_to(target)
