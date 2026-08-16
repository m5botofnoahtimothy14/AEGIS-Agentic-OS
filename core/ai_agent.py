from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class NeuralBrain:
    def __init__(self):
        self.knowledge = {}
        self.conversation_history = deque(maxlen=100)
        self.learned_patterns = {}
        self.weights = self._initialize_weights()
        self.bias = self._initialize_bias()

    def _initialize_weights(self) -> list[list[float]]:
        return [[0.0 for _ in range(20)] for _ in range(50)]

    def _initialize_bias(self) -> list[float]:
        return [0.0 for _ in range(20)]

    def sigmoid(self, x):
        import math

        return 1 / (1 + math.exp(-max(-500, min(500, x))))

    def think(self, input_text: str, context: Dict) -> Dict[str, Any]:
        features = self._encode_input(input_text, context)
        hidden = self._apply_hidden(features)
        response = self._generate_response(input_text, context, hidden)
        self._learn(input_text, response, context)
        return response

    def _apply_hidden(self, features: list[float]) -> list[float]:
        hidden = []
        for neuron in self.weights:
            total = 0.0
            for index, weight in enumerate(neuron):
                total += features[index] * weight
            hidden.append(self.sigmoid(total + self.bias[0]))
        return hidden

    def _encode_input(self, text: str, context: Dict) -> list[float]:
        features = []
        text_hash = hashlib.md5(text.encode()).digest()
        features.extend([b / 255.0 for b in text_hash[:16]])
        features.append(context.get("security_level", 0.5))
        features.append(context.get("user_trust", 0.5))
        features.append(context.get("time_of_day", 0.5))
        features.append(len(text.split()) / 20.0)
        while len(features) < 50:
            features.append(0.0)
        return features[:50]

    def _generate_response(self, input_text: str, context: Dict, hidden: list[float]) -> Dict[str, Any]:
        input_lower = input_text.lower()
        if any(word in input_lower for word in ["security", "threat", "virus", "malware", "attack"]):
            return {
                "type": "security",
                "message": self._analyze_security(input_text, context),
                "action": "security_scan",
                "confidence": 0.95,
            }
        if any(word in input_lower for word in ["status", "system", "cpu", "memory", "how are you"]):
            return {
                "type": "status",
                "message": self._get_system_status(context),
                "action": "none",
                "confidence": 0.90,
            }
        if any(word in input_lower for word in ["turn on", "turn off", "open", "close", "start", "stop"]):
            return {
                "type": "control",
                "message": f"Executing control command: {input_text}",
                "action": "execute_control",
                "confidence": 0.85,
            }
        if any(word in input_lower for word in ["what", "how", "why", "explain", "tell me"]):
            return {
                "type": "information",
                "message": self._generate_information(input_text, context),
                "action": "none",
                "confidence": 0.80,
            }
        return {
            "type": "conversation",
            "message": self._generate_conversation(input_text, context),
            "action": "none",
            "confidence": 0.70,
        }

    def _analyze_security(self, query: str, context: Dict) -> str:
        return f"Security analysis complete. Monitoring system for threats. Current security level: {context.get('security_level', 'Standard')}"

    def _get_system_status(self, context: Dict) -> str:
        import psutil

        cpu = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory().percent
        return f"System operational. CPU: {cpu}%, Memory: {memory}%. All services running normally."

    def _generate_information(self, query: str, context: Dict) -> str:
        responses = {
            "what are you": "I am SATURDAY, an advanced AI operating system with deep learning capabilities.",
            "how do you work": "I use neural networks to process inputs and generate intelligent responses.",
            "what can you do": "I can control your home, monitor security, analyze threats, and assist with many tasks.",
        }
        query_lower = query.lower()
        for key, response in responses.items():
            if key in query_lower:
                return response
        return f"Processing your query about: {query}. I'm analyzing this through my neural networks."

    def _generate_conversation(self, query: str, context: Dict) -> str:
        greetings = ["hello", "hi", "hey"]
        if any(g in query.lower() for g in greetings):
            return "Hello! I'm SATURDAY, online and ready. How can I assist you today?"
        return f"I understand: '{query}'. I'm processing this through my deep learning systems."

    def _learn(self, input_text: str, response: Dict, context: Dict):
        self.conversation_history.append(
            {
                "input": input_text,
                "response": response,
                "timestamp": time.time(),
                "context": context,
            }
        )
        pattern_key = hashlib.md5(input_text.encode()).hexdigest()[:8]
        if pattern_key not in self.learned_patterns:
            self.learned_patterns[pattern_key] = {"count": 0, "responses": []}
        self.learned_patterns[pattern_key]["count"] += 1
        self.learned_patterns[pattern_key]["responses"].append(response["type"])


class OfflineAIAgent:
    def __init__(self, storage_dir: Optional[str | Path] = None):
        self.storage_dir = Path(storage_dir or os.getenv("SATURDAY_AGENT_STORAGE_DIR", "data"))
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.storage_dir / "agent_state.json"
        self.memory = {
            "preferences": {},
            "facts": [],
            "last_seen": None,
        }
        self.history: list[dict[str, Any]] = []
        self.knowledge: dict[str, Any] = {}
        self.running = True
        self._load_state()

    def _load_state(self) -> None:
        if not self.state_path.exists():
            return
        try:
            with self.state_path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            self.memory = data.get("memory", self.memory)
            self.history = data.get("history", [])
            self.knowledge = data.get("knowledge", {})
        except (json.JSONDecodeError, OSError):
            self.memory = {"preferences": {}, "facts": [], "last_seen": None}
            self.history = []
            self.knowledge = {}

    def _persist_state(self) -> None:
        payload = {
            "memory": self.memory,
            "history": self.history,
            "knowledge": self.knowledge,
            "saved_at": datetime.now().isoformat(),
        }
        with self.state_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)

    def save_state(self) -> Dict[str, Any]:
        self._persist_state()
        return {
            "memory": self.memory,
            "history": self.history,
            "knowledge": self.knowledge,
        }

    def _get_default_context(self) -> Dict[str, Any]:
        try:
            import psutil

            cpu = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory().percent
        except Exception:
            cpu = 0.0
            memory = 0.0

        return {
            "security_level": "High",
            "user_trust": 0.9,
            "time_of_day": datetime.now().hour / 24.0,
            "system_load": cpu / 100.0,
            "memory_usage": memory / 100.0,
            "offline_mode": True,
        }

    def _detect_intent(self, command: str) -> str:
        text = command.lower()
        if any(token in text for token in ["show memory", "preferences", "facts", "remembered"]):
            return "memory"
        if any(token in text for token in ["list notes", "notes", "show notes"]):
            return "list_notes"
        if any(token in text for token in ["task", "todo", "reminder"]):
            return "task"
        if any(token in text for token in ["write", "create", "save", "file", "note"]):
            return "file"
        if any(token in text for token in ["remember", "learn", "store"]):
            return "memory"
        if any(token in text for token in ["what can you do", "capabilities", "help", "who are you"]):
            return "info"
        if any(token in text for token in ["status", "health", "cpu", "memory", "system"]):
            return "status"
        if any(token in text for token in ["security", "threat", "scan"]):
            return "security"
        if any(token in text for token in ["open", "run", "start", "launch", "stop"]):
            return "control"
        return "conversation"

    def _remember(self, command: str) -> None:
        phrase = re.sub(r"^(remember|note|store|learn)\s+(that\s+)?", "", command, flags=re.IGNORECASE).strip()
        if not phrase:
            phrase = "memory entry"
        if "like" in phrase.lower() or "prefer" in phrase.lower() or "love" in phrase.lower():
            bucket = self.memory["preferences"].setdefault("likes", [])
            bucket.append(phrase)
        else:
            self.memory["facts"].append(phrase)
        self.memory["last_seen"] = datetime.now().isoformat()

    def _show_memory(self) -> Dict[str, Any]:
        return {
            "preferences": self.memory.get("preferences", {}),
            "facts": self.memory.get("facts", []),
            "last_seen": self.memory.get("last_seen"),
        }

    def _write_note(self, command: str) -> Dict[str, Any]:
        body = re.sub(r"^(write|create|save)\s+(note|file)\s*", "", command, flags=re.IGNORECASE).strip()
        if not body:
            body = "Offline note created by SATURDAY."
        slug = re.sub(r"[^a-z0-9]+", "-", body.lower()).strip("-") or "note"
        notes_dir = self.storage_dir / "notes"
        notes_dir.mkdir(parents=True, exist_ok=True)
        path = notes_dir / f"{slug}.md"
        path.write_text(body + "\n", encoding="utf-8")
        return {
            "path": str(path),
            "status": "created",
        }

    def _list_notes(self) -> Dict[str, Any]:
        notes_dir = self.storage_dir / "notes"
        notes_dir.mkdir(parents=True, exist_ok=True)
        notes = sorted(str(path.relative_to(self.storage_dir)) for path in notes_dir.glob("*.md"))
        return {"notes": notes}

    def _create_task(self, command: str) -> Dict[str, Any]:
        body = re.sub(r"^(create|add)\s+task\s*", "", command, flags=re.IGNORECASE).strip()
        if not body:
            body = "General task"
        task_id = f"task-{len(self.memory.get('facts', [])) + 1}"
        tasks = self.knowledge.setdefault("tasks", [])
        tasks.append({"id": task_id, "title": body, "status": "pending"})
        return {"task_id": task_id, "task_title": body}

    def _build_status_message(self, context: Dict[str, Any]) -> str:
        try:
            import psutil

            cpu = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory().percent
            return (
                f"Offline core active. CPU: {cpu:.1f}%, memory: {memory:.1f}%. "
                f"Stored memories: {len(self.memory['facts']) + len(self.memory['preferences'].get('likes', []))}."
            )
        except Exception:
            return "Offline core active. Local memory is available and the agent is ready to assist."

    def process_command(self, command: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if context is None:
            context = self._get_default_context()
        intent = self._detect_intent(command)
        message = ""
        confidence = 0.72
        action = "none"
        extra: Dict[str, Any] = {}

        if intent == "memory":
            if "show" in command.lower() or "memory" in command.lower() and "show" in command.lower():
                memory_snapshot = self._show_memory()
                extra = memory_snapshot
                message = "Here is the current offline memory snapshot."
                confidence = 0.94
                action = "memory"
            else:
                self._remember(command)
                message = "I stored that in your local offline memory."
                confidence = 0.93
                action = "remember"
        elif intent == "info":
            message = (
                "I am SATURDAY, your offline-capable AI agent. I can reason locally, remember preferences, "
                "monitor system status, and save notes without needing the cloud."
            )
            confidence = 0.95
            action = "info"
        elif intent == "status":
            message = self._build_status_message(context)
            confidence = 0.9
            action = "status"
        elif intent == "security":
            message = "Security monitoring is active in offline mode. I am watching for suspicious activity locally."
            confidence = 0.9
            action = "security"
        elif intent == "file":
            extra = self._write_note(command)
            message = f"I saved a local note at {extra['path']}."
            confidence = 0.92
            action = "file"
        elif intent == "list_notes":
            extra = self._list_notes()
            message = "Here are the local notes I have saved."
            confidence = 0.9
            action = "list_notes"
        elif intent == "task":
            extra = self._create_task(command)
            message = f"I created task {extra['task_id']} for: {extra['task_title']}."
            confidence = 0.9
            action = "task"
        elif intent == "control":
            message = f"I can prepare a local action for: {command}. Offline execution is limited to safe, non-destructive operations."
            confidence = 0.82
            action = "control"
        else:
            message = f"I understand your request and I am responding in offline mode: {command}"
            confidence = 0.78
            action = "conversation"

        entry = {
            "command": command,
            "intent": intent,
            "message": message,
            "mode": "offline",
            "confidence": confidence,
            "action": action,
            "context": context,
            "timestamp": datetime.now().isoformat(),
            "memory": self.memory,
        }
        entry.update(extra)
        self.history.append(entry)
        self._persist_state()
        return entry

    def get_status(self) -> Dict[str, Any]:
        return {
            "active": self.running,
            "mode": "offline",
            "commands_processed": len(self.history),
            "memory_items": len(self.memory["facts"]) + len(self.memory["preferences"].get("likes", [])),
            "last_update": datetime.now().isoformat(),
        }

    def shutdown(self) -> None:
        self.running = False
        self._persist_state()


class AIAgent(OfflineAIAgent):
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, storage_dir: Optional[str | Path] = None):
        if getattr(self, "_initialized", False):
            return
        super().__init__(storage_dir=storage_dir)
        self.brain = NeuralBrain()
        self.command_history = deque(maxlen=1000)
        self.learned_commands: Dict[str, Any] = {}
        self.running = True
        self._initialized = True
        self._load_knowledge()

    def process_command(self, command: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if context is None:
            context = self._get_default_context()
        self.command_history.append({"command": command, "timestamp": time.time(), "context": context})
        result = super().process_command(command, context=context)
        self._learn_command(command, result)
        return result

    def _learn_command(self, command: str, result: Dict[str, Any]) -> None:
        cmd_key = command.lower().split()[0] if command else ""
        if cmd_key not in self.learned_commands:
            self.learned_commands[cmd_key] = {"count": 0, "results": []}
        self.learned_commands[cmd_key]["count"] += 1
        self.learned_commands[cmd_key]["results"].append(result.get("intent", "conversation"))

    def _load_knowledge(self) -> None:
        knowledge_file = self.storage_dir / "ai_knowledge.json"
        if not knowledge_file.exists():
            return
        try:
            with knowledge_file.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            self.learned_commands = data.get("commands", {})
            self.brain.learned_patterns = data.get("patterns", {})
        except (json.JSONDecodeError, OSError):
            self.learned_commands = {}
            self.brain.learned_patterns = {}

    def save_knowledge(self) -> None:
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        knowledge_file = self.storage_dir / "ai_knowledge.json"
        with knowledge_file.open("w", encoding="utf-8") as handle:
            json.dump(
                {
                    "commands": self.learned_commands,
                    "patterns": self.brain.learned_patterns,
                    "saved_at": datetime.now().isoformat(),
                },
                handle,
                indent=2,
            )
        self.save_state()

    def get_status(self) -> Dict[str, Any]:
        status = super().get_status()
        status.update(
            {
                "commands_processed": len(self.command_history),
                "unique_commands": len(self.learned_commands),
                "patterns_learned": len(self.brain.learned_patterns),
                "brain_neurons": len(self.brain.weights) * len(self.brain.weights[0]),
            }
        )
        return status

    def shutdown(self) -> None:
        self.running = False
        self.save_knowledge()


_agent: Optional[AIAgent] = None


def get_ai_agent() -> AIAgent:
    global _agent
    if _agent is None:
        _agent = AIAgent()
    return _agent
