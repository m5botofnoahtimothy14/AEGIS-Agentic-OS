"""
SATURDAY 3.0 -- Voice Command Handler with Real Integration Engine
Wires all 72+ capabilities through AI governance.
"""
import logging
import re
import json
import time
from typing import Dict, Any, Optional
from core.system_control import get_system_controller, VoiceCommandParser
from core.ai_governance import get_governance_engine, ActionRequest, ActionCategory
from core.real_integration import get_real_integration, RealIntegrationEngine

logger = logging.getLogger("SATURDAY.VoiceIntegration")


class VoiceCommandHandler:
    """Voice/text command handler using RealIntegrationEngine with governance."""

    def __init__(
        self,
        event_bus=None,
        system_controller=None,
        governance_engine=None,
        real_integration: RealIntegrationEngine = None,
    ):
        self.event_bus = event_bus
        self.system = system_controller or get_system_controller(event_bus)
        self.governance = governance_engine or get_governance_engine(event_bus)
        self.real = real_integration or get_real_integration(event_bus, self.governance)
        self.parser = VoiceCommandParser(self.system)

        # Map actions to real_integration methods
        self.handlers = {
            # System & Apps
            "open_app": lambda p: self.real.open_application(p.get("app", "")),
            "list_processes": lambda p: self.real.list_processes(p.get("limit", 30)),
            "kill_process": lambda p: self.real.kill_process(p.get("pid"), p.get("name")),
            "system_info": lambda p: self.real.system_info(),
            "disk_info": lambda p: self.real.disk_info(),
            "network_info": lambda p: self.real.network_info(),
            "env_vars": lambda p: self.real.env_vars(p.get("filter_key")),
            "set_env": lambda p: self.real.set_env(p.get("key"), p.get("value", "")),
            "scheduled_tasks": lambda p: self.real.scheduled_tasks(),
            "service_status": lambda p: self.real.service_status(p.get("name")),
            "event_logs": lambda p: self.real.event_logs(p.get("log_name", "System"), p.get("count", 20)),
            "registry_read": lambda p: self.real.registry_read(p.get("key", "")),
            # Files
            "list_directory": lambda p: self.real.list_directory(p.get("path", "."), p.get("hidden", False)),
            "search_files": lambda p: self.real.search_files(p.get("path", "."), p.get("pattern", "*"), p.get("recursive", True), p.get("limit", 100)),
            "search_content": lambda p: self.real.search_content(p.get("path", "."), p.get("pattern", ""), p.get("extensions"), p.get("limit", 50)),
            "read_file": lambda p: self.real.read_file(p.get("path", ""), p.get("lines")),
            "write_file": lambda p: self.real.write_file(p.get("path", ""), p.get("content", ""), p.get("append", False)),
            "copy_file": lambda p: self.real.copy_file(p.get("src"), p.get("dst")),
            "move_file": lambda p: self.real.move_file(p.get("src"), p.get("dst")),
            "delete_file": lambda p: self.real.delete_file(p.get("path", ""), p.get("force", False)),
            "mkdir": lambda p: self.real.mkdir(p.get("path", "")),
            "file_info": lambda p: self.real.file_info(p.get("path", "")),
            "hash_file": lambda p: self.real.hash_file(p.get("path", ""), p.get("algo", "sha256")),
            # Commands
            "execute": lambda p: self.real.execute(p.get("command", ""), p.get("timeout", 30)),
            "git_status": lambda p: self.real.git_status(p.get("repo", ".")),
            "git_log": lambda p: self.real.git_log(p.get("repo", "."), p.get("count", 20)),
            "git_diff": lambda p: self.real.git_diff(p.get("repo", "."), p.get("target")),
            "git_commit": lambda p: self.real.git_commit(p.get("repo", "."), p.get("message", ""), p.get("files", ".")),
            "python_run": lambda p: self.real.python_run(p.get("script", ""), p.get("args", "")),
            "docker": lambda p: self.real.docker(p.get("command", "")),
            # Web
            "web_search": lambda p: self.real.web_search(p.get("query", ""), p.get("engine", "google")),
            "open_url": lambda p: self.real.open_url(p.get("url", "")),
            "http_get": lambda p: self.real.http_get(p.get("url", ""), p.get("headers"), p.get("params")),
            "http_post": lambda p: self.real.http_post(p.get("url", ""), p.get("data"), p.get("json_data"), p.get("headers")),
            "download": lambda p: self.real.download(p.get("url", ""), p.get("dest")),
            "dns_lookup": lambda p: self.real.dns_lookup(p.get("host", "")),
            "port_scan": lambda p: self.real.port_scan(p.get("host", ""), p.get("ports")),
            # Media
            "play_media": lambda p: self.real.play_media(p.get("query", ""), p.get("platform", "youtube")),
            "play_local": lambda p: self.real.play_local(p.get("path", "")),
            "tts": lambda p: self.real.tts(p.get("text", "")),
            "screenshot": lambda p: self.real.screenshot(p.get("path")),
            "list_media": lambda p: self.real.list_media(p.get("directory")),
            "media_info": lambda p: self.real.media_info(p.get("path", "")),
            "convert_media": lambda p: self.real.convert_media(p.get("inp", ""), p.get("out", ""), p.get("opts", "")),
            "clipboard_get": lambda p: self.real.clipboard_get(),
            "clipboard_set": lambda p: self.real.clipboard_set(p.get("text", "")),
            # Communication
            "notify": lambda p: self.real.notify(p.get("title", "SATURDAY"), p.get("message", "")),
            "send_email": lambda p: self.real.send_email(p.get("to", ""), p.get("subject", ""), p.get("body", ""), p.get("smtp", "smtp.gmail.com"), p.get("port", 587), p.get("user", ""), p.get("passwd", "")),
            "port_check": lambda p: self.real.port_check(p.get("port", 0)),
            "local_ip": lambda p: self.real.local_ip(),
            "ping": lambda p: self.real.ping(p.get("host", ""), p.get("count", 4)),
            "traceroute": lambda p: self.real.traceroute(p.get("host", "")),
            # Dev
            "npm": lambda p: self.real.npm(p.get("command", ""), p.get("cwd", ".")),
            "pip": lambda p: self.real.pip(p.get("command", "")),
            "count_loc": lambda p: self.real.count_loc(p.get("path", "."), p.get("exts")),
            "run_tests": lambda p: self.real.run_tests(p.get("path", "."), p.get("framework", "pytest")),
            "lint": lambda p: self.real.lint(p.get("path", "."), p.get("tool", "ruff")),
            "listening_ports": lambda p: self.real.listening_ports(),
            "process_tree": lambda p: self.real.process_tree(p.get("pid")),
            "health_dashboard": lambda p: self.real.health_dashboard(),
            # Window management
            "list_windows": lambda p: self.real.list_windows(),
            "focus_window": lambda p: self.real.focus_window(p.get("title", "")),
            "minimize_window": lambda p: self.real.minimize_window(p.get("title", "")),
            "maximize_window": lambda p: self.real.maximize_window(p.get("title", "")),
            # Keyboard/Mouse
            "type_text": lambda p: self.real.type_text(p.get("text", ""), p.get("interval", 0.05)),
            "press_key": lambda p: self.real.press_key(p.get("key", "")),
            "hotkey": lambda p: self.real.hotkey(*p.get("keys", [])),
            "click": lambda p: self.real.click(p.get("x"), p.get("y")),
            # Security/Hardware
            "security_scan": lambda p: self.real.security_scan(),
            "usb_devices": lambda p: self.real.usb_devices(),
            "gpu_info": lambda p: self.real.gpu_info(),
            "battery_status": lambda p: self.real.battery_status(),
            "temperatures": lambda p: self.real.temperatures(),
            "firewall_status": lambda p: self.real.firewall_status(),
            "defender_status": lambda p: self.real.defender_status(),
            "user_accounts": lambda p: self.real.user_accounts(),
            # Archive
            "zip_directory": lambda p: self.real.zip_directory(p.get("src", ""), p.get("dest", "")),
            "unzip": lambda p: self.real.unzip(p.get("src", ""), p.get("dest", "")),
            "file_permissions": lambda p: self.real.file_permissions(p.get("path", "")),
            # Demo showcase (autonomous)
            "demo_showcase": lambda p: self._handle_demo(p),
            "demo": lambda p: self._handle_demo(p),
            # Weather
            "weather": lambda p: self._handle_weather(p),
            # Legacy (system_control)
            "open_file": lambda p: self.system.open_file(p.get("path", "")),
            "open_folder": lambda p: self.system.open_folder(p.get("path", "")),
        }

        if self.event_bus:
            self.event_bus.subscribe("voice_command", self.handle_command)
            self.event_bus.subscribe("text_command", self.handle_command)
            self.event_bus.subscribe("governance_confirm", self._handle_governance_confirm)

    def _handle_governance_confirm(self, data: Dict):
        if self.event_bus:
            self.event_bus.publish("governance_confirm", data)

    def _handle_demo(self, params: Dict) -> Dict:
        try:
            if self.event_bus:
                self.event_bus.publish("demo_showcase", params or {"source": "voice"})
            return {"success": True, "message": "Autonomous demo started — SATURDAY will speak and act through each feature now. Watch the overlay flash, mouse move, and listen to each feature."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_weather(self, params: Dict) -> Dict:
        location = params.get("location", "")
        if not location:
            raw = params.get("_raw", "")
            m = re.search(
                r"(?:weather|forecast|temperature|how(?:'s| is))\s+(?:in |for |at )?(.+?)(?:\?|$)",
                raw, re.IGNORECASE,
            )
            if m:
                location = m.group(1).strip()
        try:
            from core.services.weather_service import WeatherService
            ws = WeatherService()
            return ws.get_current_weather(location)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def handle_command(self, data: Any) -> Dict[str, Any]:
        """Main entry point for voice/text commands."""
        if isinstance(data, dict):
            command = data.get("command", data.get("text", ""))
            context = data.get("context", "voice")
            target = data.get("target", "saturday")
            params = data.get("params", {})
        else:
            command = str(data)
            context = "voice"
            target = "saturday"
            params = {}

        if not command or not command.strip():
            return {"success": False, "error": "Empty command"}

        logger.info(f"Processing command: {command[:100]}")

        # Try natural language dispatch first
        dispatch_result = self.real.dispatch(command)
        if dispatch_result.get("success") is not None:
            # Dispatch handled it
            action = "dispatch"
        else:
            # Fall back to parser
            parsed = self.parser.parse(command)
            action = parsed.get("action", "execute")
            params.update({k: v for k, v in parsed.items() if k not in ["action", "context", "original_command"]})

        # Add governance context
        params["context"] = context
        params["original_command"] = command

        return self._execute_with_governance(action, params, context)

    def _execute_with_governance(self, action: str, params: Dict, context: str) -> Dict:
        """Execute action with governance checks."""
        # Determine category
        category_map = {
            "open_app": ActionCategory.SYSTEM_CONTROL,
            "list_processes": ActionCategory.PROCESS_MANAGEMENT,
            "kill_process": ActionCategory.PROCESS_MANAGEMENT,
            "system_info": ActionCategory.SYSTEM_CONTROL,
            "disk_info": ActionCategory.SYSTEM_CONTROL,
            "network_info": ActionCategory.SYSTEM_CONTROL,
            "env_vars": ActionCategory.SYSTEM_CONTROL,
            "set_env": ActionCategory.SYSTEM_CONTROL,
            "scheduled_tasks": ActionCategory.SYSTEM_CONTROL,
            "service_status": ActionCategory.SYSTEM_CONTROL,
            "event_logs": ActionCategory.SYSTEM_CONTROL,
            "registry_read": ActionCategory.SYSTEM_CONTROL,
            "list_directory": ActionCategory.FILE_OPERATION,
            "search_files": ActionCategory.FILE_OPERATION,
            "search_content": ActionCategory.FILE_OPERATION,
            "read_file": ActionCategory.FILE_OPERATION,
            "write_file": ActionCategory.FILE_OPERATION,
            "copy_file": ActionCategory.FILE_OPERATION,
            "move_file": ActionCategory.FILE_OPERATION,
            "delete_file": ActionCategory.FILE_OPERATION,
            "mkdir": ActionCategory.FILE_OPERATION,
            "file_info": ActionCategory.FILE_OPERATION,
            "hash_file": ActionCategory.FILE_OPERATION,
            "execute": ActionCategory.SYSTEM_CONTROL,
            "git_status": ActionCategory.SYSTEM_CONTROL,
            "git_log": ActionCategory.SYSTEM_CONTROL,
            "git_diff": ActionCategory.SYSTEM_CONTROL,
            "git_commit": ActionCategory.SYSTEM_CONTROL,
            "python_run": ActionCategory.SYSTEM_CONTROL,
            "docker": ActionCategory.SYSTEM_CONTROL,
            "web_search": ActionCategory.NETWORK_ACCESS,
            "open_url": ActionCategory.NETWORK_ACCESS,
            "http_get": ActionCategory.NETWORK_ACCESS,
            "http_post": ActionCategory.NETWORK_ACCESS,
            "download": ActionCategory.NETWORK_ACCESS,
            "dns_lookup": ActionCategory.NETWORK_ACCESS,
            "port_scan": ActionCategory.NETWORK_ACCESS,
            "play_media": ActionCategory.NETWORK_ACCESS,
            "play_local": ActionCategory.SYSTEM_CONTROL,
            "tts": ActionCategory.SYSTEM_CONTROL,
            "screenshot": ActionCategory.FILE_OPERATION,
            "list_media": ActionCategory.FILE_OPERATION,
            "media_info": ActionCategory.FILE_OPERATION,
            "convert_media": ActionCategory.FILE_OPERATION,
            "clipboard_get": ActionCategory.USER_DATA_ACCESS,
            "clipboard_set": ActionCategory.USER_DATA_ACCESS,
            "notify": ActionCategory.EXTERNAL_COMMUNICATION,
            "send_email": ActionCategory.EXTERNAL_COMMUNICATION,
            "port_check": ActionCategory.NETWORK_ACCESS,
            "local_ip": ActionCategory.NETWORK_ACCESS,
            "ping": ActionCategory.NETWORK_ACCESS,
            "traceroute": ActionCategory.NETWORK_ACCESS,
            "npm": ActionCategory.SYSTEM_CONTROL,
            "pip": ActionCategory.SYSTEM_CONTROL,
            "count_loc": ActionCategory.SYSTEM_CONTROL,
            "run_tests": ActionCategory.SYSTEM_CONTROL,
            "lint": ActionCategory.SYSTEM_CONTROL,
            "listening_ports": ActionCategory.SYSTEM_CONTROL,
            "process_tree": ActionCategory.PROCESS_MANAGEMENT,
            "health_dashboard": ActionCategory.SYSTEM_CONTROL,
            "list_windows": ActionCategory.SYSTEM_CONTROL,
            "focus_window": ActionCategory.SYSTEM_CONTROL,
            "minimize_window": ActionCategory.SYSTEM_CONTROL,
            "maximize_window": ActionCategory.SYSTEM_CONTROL,
            "type_text": ActionCategory.SYSTEM_CONTROL,
            "press_key": ActionCategory.SYSTEM_CONTROL,
            "hotkey": ActionCategory.SYSTEM_CONTROL,
            "click": ActionCategory.SYSTEM_CONTROL,
            "security_scan": ActionCategory.SYSTEM_CONTROL,
            "usb_devices": ActionCategory.SYSTEM_CONTROL,
            "gpu_info": ActionCategory.SYSTEM_CONTROL,
            "battery_status": ActionCategory.SYSTEM_CONTROL,
            "temperatures": ActionCategory.SYSTEM_CONTROL,
            "firewall_status": ActionCategory.SYSTEM_CONTROL,
            "defender_status": ActionCategory.SYSTEM_CONTROL,
            "user_accounts": ActionCategory.SYSTEM_CONTROL,
            "zip_directory": ActionCategory.FILE_OPERATION,
            "unzip": ActionCategory.FILE_OPERATION,
            "file_permissions": ActionCategory.FILE_OPERATION,
            "open_file": ActionCategory.FILE_OPERATION,
            "open_folder": ActionCategory.FILE_OPERATION,
            "dispatch": ActionCategory.SYSTEM_CONTROL,
        }

        category = category_map.get(action, ActionCategory.SYSTEM_CONTROL)

        request = ActionRequest(
            action=action,
            category=category,
            parameters=params,
            context=context,
            user_confirmed=params.get("confirmed", False),
            admin_approved=params.get("admin_approved", False),
        )

        decision = self.governance.evaluate(request)

        if not decision.allowed:
            if decision.requires_confirmation:
                if self.event_bus:
                    self.event_bus.publish("voice_response", {
                        "text": f"This action requires confirmation: {decision.reason}. {decision.alternative or 'Say confirm to proceed.'}",
                        "governance": {
                            "audit_id": decision.audit_id,
                            "requires_confirmation": True,
                            "risk_level": decision.risk_level.value,
                        },
                    })
                return {
                    "success": False,
                    "governance_blocked": True,
                    "reason": decision.reason,
                    "requires_confirmation": True,
                    "audit_id": decision.audit_id,
                    "risk_level": decision.risk_level.value,
                }
            else:
                if self.event_bus:
                    self.event_bus.publish("voice_response", {
                        "text": f"Action blocked by governance: {decision.reason}",
                        "governance": {
                            "audit_id": decision.audit_id,
                            "risk_level": decision.risk_level.value,
                        },
                    })
                return {
                    "success": False,
                    "governance_blocked": True,
                    "reason": decision.reason,
                    "audit_id": decision.audit_id,
                    "risk_level": decision.risk_level.value,
                }

        handler = self.handlers.get(action)
        if not handler:
            return {"success": False, "error": f"No handler for action: {action}"}

        try:
            result = handler(params)

            if context == "voice" and self.event_bus:
                response_text = self._generate_response(action, result, params.get("original_command", ""))
                self.event_bus.publish("voice_response", {"text": response_text})

            return {"success": True, "result": result, "action": action}

        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return {"success": False, "error": str(e)}

    def _generate_response(self, action: str, result: Dict, original: str) -> str:
        """Generate natural language response."""
        if not result.get("success"):
            return f"Sorry, I couldn't complete that. {result.get('error', 'Unknown error')}"

        responses = {
            "open_app": f"Opened {result.get('message', 'the application')}",
            "list_processes": f"Found {result.get('total', 0)} processes",
            "kill_process": result.get("message", "Process terminated"),
            "system_info": f"CPU {result.get('cpu_percent', 0)}%, Memory {result.get('mem_percent', 0)}%, Disk {result.get('disk_percent', 0)}%",
            "disk_info": f"Found {len(result.get('partitions', []))} partitions",
            "network_info": f"Found {len(result.get('interfaces', []))} interfaces",
            "env_vars": f"Found {result.get('count', 0)} environment variables",
            "set_env": "Environment variable set",
            "list_directory": f"Found {result.get('total', 0)} items",
            "search_files": f"Found {result.get('count', 0)} matches",
            "search_content": f"Found {result.get('count', 0)} matches",
            "read_file": "File read successfully",
            "write_file": "File written successfully",
            "copy_file": "File copied",
            "move_file": "File moved",
            "delete_file": "File deleted",
            "mkdir": "Directory created",
            "file_info": f"File info: {result.get('size', '')}",
            "hash_file": f"Hash: {result.get('hash', '')[:16]}...",
            "execute": f"Command executed: {result.get('stdout', 'done')[:100]}",
            "git_status": f"Git status: {result.get('stdout', '')[:100]}",
            "web_search": f"Opened search for {params.get('query', '')}",
            "play_media": "Playing media",
            "play_local": "Playing local file",
            "tts": "Spoken",
            "screenshot": f"Screenshot saved",
            "notify": "Notification sent",
            "send_email": "Email sent",
            "ping": f"Ping result: {result.get('stdout', '')[:200]}",
            "local_ip": f"Local IP: {result.get('ip', '')}",
            "health_dashboard": f"System health: CPU {result.get('system', {}).get('cpu_percent', 0)}% MEM {result.get('system', {}).get('mem_percent', 0)}% DISK {result.get('system', {}).get('disk_percent', 0)}%",
            "list_windows": f"Found {result.get('count', 0)} windows",
            "focus_window": "Window focused",
            "minimize_window": "Window minimized",
            "maximize_window": "Window maximized",
            "type_text": "Text typed",
            "press_key": "Key pressed",
            "hotkey": "Hotkey executed",
            "click": "Clicked",
            "security_scan": f"Scan complete. Threats: {result.get('threat_count', 0)}",
            "gpu_info": "GPU info retrieved",
            "battery_status": f"Battery: {result.get('percent', 0)}%",
            "temperatures": "Temperatures retrieved",
            "firewall_status": "Firewall status retrieved",
            "defender_status": "Defender status retrieved",
            "dispatch": result.get("message", "Command completed"),
        }

        return responses.get(action, "Command completed")


# Global instance
_voice_handler = None


def get_voice_handler(event_bus=None, real_integration=None) -> VoiceCommandHandler:
    global _voice_handler
    if _voice_handler is None:
        _voice_handler = VoiceCommandHandler(event_bus, real_integration=real_integration)
    return _voice_handler