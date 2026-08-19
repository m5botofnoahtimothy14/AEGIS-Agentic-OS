import os
import sys
import subprocess
import webbrowser
import json
import logging
import threading
import time
import platform
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
import psutil
import pyautogui
import pygetwindow as gw

logger = logging.getLogger("SATURDAY.SystemControl")

class SystemController:
    def __init__(self, event_bus=None):
        self.event_bus = event_bus
        self.os_type = platform.system()
        self._app_cache = {}
        self._build_app_index()

    def _build_app_index(self):
        """Index common applications for quick launching"""
        if self.os_type == "Windows":
            paths_to_search = [
                os.environ.get("ProgramFiles", "C:\\Program Files"),
                os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"),
                os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs"),
                os.path.join(os.environ.get("APPDATA", ""), "Microsoft\\Windows\\Start Menu\\Programs"),
                "C:\\Windows\\System32",
            ]
            for base in paths_to_search:
                if os.path.exists(base):
                    for root, dirs, files in os.walk(base):
                        for f in files:
                            if f.endswith(('.exe', '.lnk', '.bat', '.cmd')):
                                name = os.path.splitext(f)[0].lower()
                                if name not in self._app_cache:
                                    self._app_cache[name] = os.path.join(root, f)
                                if len(self._app_cache) > 500:
                                    return

    def execute_command(self, command: str, shell: bool = True, timeout: int = 30) -> Dict[str, Any]:
        """Execute a shell command and return result"""
        try:
            result = subprocess.run(
                command,
                shell=shell,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Command timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def open_application(self, app_name: str) -> Dict[str, Any]:
        """Open an application by name"""
        app_name = app_name.lower().strip()
        
        # Direct matches
        direct_map = {
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "cmd": "cmd.exe",
            "command prompt": "cmd.exe",
            "powershell": "powershell.exe",
            "terminal": "wt.exe",
            "explorer": "explorer.exe",
            "file explorer": "explorer.exe",
            "settings": "ms-settings:",
            "control panel": "control.exe",
            "task manager": "taskmgr.exe",
            "registry editor": "regedit.exe",
            "device manager": "devmgmt.msc",
            "disk management": "diskmgmt.msc",
            "services": "services.msc",
            "event viewer": "eventvwr.msc",
            "paint": "mspaint.exe",
            "snipping tool": "snippingtool.exe",
            "wordpad": "write.exe",
            "charmap": "charmap.exe",
            "magnifier": "magnify.exe",
            "narrator": "narrator.exe",
            "on-screen keyboard": "osk.exe",
            "remote desktop": "mstsc.exe",
            "system info": "msinfo32.exe",
        }
        
        if app_name in direct_map:
            try:
                if direct_map[app_name].endswith(":"):
                    subprocess.Popen(["start", "", direct_map[app_name]], shell=True)
                else:
                    subprocess.Popen(direct_map[app_name])
                return {"success": True, "message": f"Opened {app_name}"}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        # Search indexed apps
        if app_name in self._app_cache:
            try:
                path = self._app_cache[app_name]
                if path.endswith('.lnk'):
                    os.startfile(path)
                else:
                    subprocess.Popen(path)
                return {"success": True, "message": f"Opened {app_name}"}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        # Try direct execution
        try:
            subprocess.Popen(app_name)
            return {"success": True, "message": f"Attempted to open {app_name}"}
        except Exception as e:
            return {"success": False, "error": f"Application not found: {app_name}"}

    def open_file(self, path: str) -> Dict[str, Any]:
        """Open a file with default application"""
        path = os.path.expanduser(path)
        if not os.path.exists(path):
            return {"success": False, "error": f"File not found: {path}"}
        try:
            if self.os_type == "Windows":
                os.startfile(path)
            elif self.os_type == "Darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
            return {"success": True, "message": f"Opened {path}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def open_folder(self, path: str) -> Dict[str, Any]:
        """Open a folder in file explorer"""
        path = os.path.expanduser(path)
        if not os.path.exists(path):
            return {"success": False, "error": f"Folder not found: {path}"}
        try:
            if self.os_type == "Windows":
                subprocess.Popen(["explorer", path])
            elif self.os_type == "Darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
            return {"success": True, "message": f"Opened folder {path}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def web_search(self, query: str, engine: str = "duckduckgo") -> Dict[str, Any]:
        """Perform a web search"""
        engines = {
            "duckduckgo": f"https://duckduckgo.com/?q={query}",
            "google": f"https://www.google.com/search?q={query}",
            "bing": f"https://www.bing.com/search?q={query}",
            "github": f"https://github.com/search?q={query}",
            "stackoverflow": f"https://stackoverflow.com/search?q={query}",
            "youtube": f"https://www.youtube.com/results?search_query={query}",
        }
        url = engines.get(engine.lower(), engines["duckduckgo"])
        try:
            webbrowser.open(url)
            return {"success": True, "url": url}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def open_url(self, url: str) -> Dict[str, Any]:
        """Open a URL in default browser"""
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        try:
            webbrowser.open(url)
            return {"success": True, "url": url}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def play_media(self, query: str, platform: str = "youtube") -> Dict[str, Any]:
        """Play media (music/video)"""
        platforms = {
            "youtube": f"https://www.youtube.com/results?search_query={query}",
            "spotify": f"https://open.spotify.com/search/{query}",
            "soundcloud": f"https://soundcloud.com/search?q={query}",
        }
        url = platforms.get(platform.lower(), platforms["youtube"])
        try:
            webbrowser.open(url)
            return {"success": True, "url": url}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def system_action(self, action: str) -> Dict[str, Any]:
        """Perform system-level actions"""
        actions = {
            "shutdown": "shutdown /s /t 10",
            "restart": "shutdown /r /t 10",
            "sleep": "rundll32.exe powrprof.dll,SetSuspendState 0,1,0",
            "hibernate": "shutdown /h",
            "lock": "rundll32.exe user32.dll,LockWorkStation",
            "logoff": "shutdown /l",
            "volume_up": "nircmd.exe changesysvolume 5000",
            "volume_down": "nircmd.exe changesysvolume -5000",
            "mute": "nircmd.exe mutesysvolume 1",
            "unmute": "nircmd.exe mutesysvolume 0",
            "brightness_up": "nircmd.exe changebrightness 10",
            "brightness_down": "nircmd.exe changebrightness -10",
        }
        
        if action.lower() in actions:
            return self.execute_command(actions[action.lower()])
        
        # Special actions
        if action.lower() == "empty_recycle_bin":
            try:
                import winshell
                winshell.recycle_bin().empty(confirm=False, show_progress=False, sound=True)
                return {"success": True, "message": "Recycle bin emptied"}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        if action.lower() == "clear_temp":
            try:
                temp_dir = os.environ.get("TEMP", "C:\\Windows\\Temp")
                for root, dirs, files in os.walk(temp_dir):
                    for f in files:
                        try:
                            os.remove(os.path.join(root, f))
                        except:
                            pass
                return {"success": True, "message": "Temp files cleared"}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        return {"success": False, "error": f"Unknown action: {action}"}

    def get_system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information"""
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "os": f"{platform.system()} {platform.release()}",
            "hostname": platform.node(),
            "cpu_percent": cpu,
            "cpu_count": psutil.cpu_count(),
            "memory": {
                "total_gb": round(mem.total / (1024**3), 2),
                "used_gb": round(mem.used / (1024**3), 2),
                "available_gb": round(mem.available / (1024**3), 2),
                "percent": mem.percent
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "percent": disk.percent
            },
            "boot_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(psutil.boot_time())),
            "python_version": sys.version.split()[0],
        }

    def get_running_processes(self, limit: int = 20) -> List[Dict]:
        """Get running processes"""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
            try:
                p = proc.info
                processes.append({
                    "pid": p['pid'],
                    "name": p['name'],
                    "cpu": round(p['cpu_percent'] or 0, 1),
                    "memory": round(p['memory_percent'] or 0, 1),
                    "status": p['status']
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return sorted(processes, key=lambda x: x['cpu'], reverse=True)[:limit]

    def kill_process(self, pid: int) -> Dict[str, Any]:
        """Kill a process by PID"""
        try:
            proc = psutil.Process(pid)
            proc.terminate()
            return {"success": True, "message": f"Process {pid} terminated"}
        except psutil.NoSuchProcess:
            return {"success": False, "error": "Process not found"}
        except psutil.AccessDenied:
            return {"success": False, "error": "Access denied"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def type_text(self, text: str, interval: float = 0.05) -> Dict[str, Any]:
        """Type text using pyautogui"""
        try:
            pyautogui.write(text, interval=interval)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def press_key(self, key: str) -> Dict[str, Any]:
        """Press a key"""
        try:
            pyautogui.press(key)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def hotkey(self, *keys) -> Dict[str, Any]:
        """Press a hotkey combination"""
        try:
            pyautogui.hotkey(*keys)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def click(self, x: int = None, y: int = None) -> Dict[str, Any]:
        """Click at position"""
        try:
            if x is not None and y is not None:
                pyautogui.click(x, y)
            else:
                pyautogui.click()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def screenshot(self, path: str = None) -> Dict[str, Any]:
        """Take a screenshot"""
        try:
            if path is None:
                path = os.path.join(os.path.expanduser("~"), "Pictures", f"saturday_screenshot_{int(time.time())}.png")
            img = pyautogui.screenshot()
            img.save(path)
            return {"success": True, "path": path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_active_window(self) -> Dict[str, Any]:
        """Get currently active window"""
        try:
            win = gw.getActiveWindow()
            if win:
                return {
                    "title": win.title,
                    "left": win.left,
                    "top": win.top,
                    "width": win.width,
                    "height": win.height
                }
        except:
            pass
        return {"title": "Unknown"}

    def list_windows(self) -> List[Dict]:
        """List all open windows"""
        windows = []
        try:
            for win in gw.getAllWindows():
                if win.title and win.visible:
                    windows.append({
                        "title": win.title,
                        "left": win.left,
                        "top": win.top,
                        "width": win.width,
                        "height": win.height
                    })
        except:
            pass
        return windows

    def focus_window(self, title_contains: str) -> Dict[str, Any]:
        """Focus a window by title"""
        try:
            for win in gw.getAllWindows():
                if title_contains.lower() in win.title.lower():
                    win.activate()
                    return {"success": True, "window": win.title}
            return {"success": False, "error": "Window not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}


# Voice command parser for natural language
class VoiceCommandParser:
    def __init__(self, controller: SystemController):
        self.controller = controller

    def parse(self, command: str) -> Dict[str, Any]:
        """Parse natural language command into action"""
        cmd = command.lower().strip()
        
        # Open app
        if any(cmd.startswith(x) for x in ["open ", "launch ", "start ", "run "]):
            app = cmd.split(" ", 1)[1] if " " in cmd else ""
            return {"action": "open_app", "app": app}
        
        # Open file/folder
        if any(cmd.startswith(x) for x in ["open file ", "open folder ", "open directory "]):
            path = cmd.split(" ", 2)[2] if len(cmd.split(" ")) > 2 else ""
            return {"action": "open_file", "path": path}
        
        # Web search
        if any(cmd.startswith(x) for x in ["search ", "google ", "look up ", "find "]):
            query = cmd.split(" ", 1)[1] if " " in cmd else ""
            return {"action": "web_search", "query": query}
        
        # Play media
        if any(cmd.startswith(x) for x in ["play ", "play music ", "play song ", "play video "]):
            query = cmd.split(" ", 1)[1] if " " in cmd else ""
            return {"action": "play_media", "query": query}
        
        # System actions
        system_actions = {
            "shutdown": "shutdown",
            "restart": "restart",
            "sleep": "sleep",
            "hibernate": "hibernate",
            "lock": "lock",
            "log off": "logoff",
            "empty recycle bin": "empty_recycle_bin",
            "clear temp": "clear_temp",
        }
        for phrase, action in system_actions.items():
            if phrase in cmd:
                return {"action": "system_action", "system_action": action}
        
        # Volume/brightness
        if "volume up" in cmd:
            return {"action": "system_action", "system_action": "volume_up"}
        if "volume down" in cmd:
            return {"action": "system_action", "system_action": "volume_down"}
        if "mute" in cmd:
            return {"action": "system_action", "system_action": "mute"}
        if "unmute" in cmd:
            return {"action": "system_action", "system_action": "unmute"}
        
        # System info
        if any(x in cmd for x in ["system info", "system status", "cpu", "memory", "disk"]):
            return {"action": "system_info"}
        
        # Default: treat as command to execute
        return {"action": "execute", "command": command}


# Global instance
_system_controller = None

def get_system_controller(event_bus=None) -> SystemController:
    global _system_controller
    if _system_controller is None:
        _system_controller = SystemController(event_bus)
    return _system_controller