import os
import json
import structlog
import asyncio
import random
import time
from datetime import datetime
from pathlib import Path

logger = structlog.get_logger("SATURDAY.AI.LLM")


class BuiltinBrain:
    """Built-in conversational brain when no local LLM is available."""

    PERSONALITY = (
        "You are SATURDAY, a warm, concise, human-like AI assistant. "
        "You speak naturally like a trusted colleague. "
        "Keep responses short and helpful. "
        "You are running on the user's local machine."
    )

    def __init__(self):
        self.context = []
        self.last_topic = None

    def respond(self, user_input: str) -> str:
        text = user_input.strip().lower()
        now = datetime.now()
        hour = now.hour

        greetings = ["hello", "hi", "hey", "good morning", "good afternoon", "good evening", "howdy", "sup"]
        if any(g in text for g in greetings):
            if hour < 12:
                return random.choice([
                    "Good morning. SATURDAY is online and ready.",
                    "Morning. What can I do for you?",
                    "Hey there. Systems are running smooth. What's up?",
                ])
            elif hour < 17:
                return random.choice([
                    "Hey. SATURDAY here. What do you need?",
                    "Good afternoon. All systems nominal. How can I help?",
                ])
            else:
                return random.choice([
                    "Good evening. SATURDAY is at your service.",
                    "Evening. Everything's running. What can I help with?",
                ])

        if any(w in text for w in ["how are you", "how are you doing", "how's it going", "you good"]):
            return random.choice([
                "All systems running smooth. How can I help you?",
                "I'm doing great, thanks for asking. What do you need?",
                "Running at full capacity. What can I do for you?",
            ])

        if any(w in text for w in ["who are you", "what are you", "your name", "tell me about yourself"]):
            return "I'm SATURDAY, your personal AI operating system. Think of me as your digital assistant - I can help with tasks, answer questions, manage your system, and keep things running smoothly."

        if any(w in text for w in ["what time", "what's the time", "current time", "tell me the time"]):
            return f"It's {now.strftime('%I:%M %p')}."

        if any(w in text for w in ["what date", "what's the date", "today's date", "what day"]):
            return f"Today is {now.strftime('%A, %B %d, %Y')}."

        if any(w in text for w in ["thank", "thanks", "appreciate"]):
            return random.choice([
                "You're welcome. Let me know if you need anything else.",
                "Happy to help.",
                "Anytime.",
            ])

        if any(w in text for w in ["status", "system status", "how's the system", "are you running"]):
            return "All systems are online and running. Voice, web interface, and core modules are active."

        if any(w in text for w in ["help", "what can you do", "capabilities", "features"]):
            return (
                "I can help with quite a bit. Here's what I do: "
                "voice commands, web search, task management, system monitoring, "
                "file operations, communication, and general conversation. "
                "Just ask naturally."
            )

        if any(w in text for w in ["shut down", "shutdown", "turn off", "sleep", "goodbye", "bye"]):
            return "Shutting down gracefully. See you next time."

        if any(w in text for w in ["joke", "funny", "make me laugh"]):
            jokes = [
                "Why do programmers prefer dark mode? Because light attracts bugs.",
                "There are only 10 types of people in the world: those who understand binary and those who don't.",
                "A SQL query walks into a bar, sees two tables and asks: Can I join you?",
                "Why was the JavaScript developer sad? Because he didn't Node how to Express himself.",
            ]
            return random.choice(jokes)

        if any(w in text for w in ["weather", "forecast"]):
            return "I don't have weather data right now, but I can help you check it if you connect a weather service."

        if any(w in text for w in ["music", "play", "song"]):
            return "Music playback is available through the web interface. Want me to help set that up?"

        if any(w in text for w in ["search", "look up", "google", "find"]):
            query = text
            for word in ["search for", "look up", "google", "find"]:
                query = query.replace(word, "").strip()
            return f"I'd search for '{query}' but the web search module needs configuration. Check the web interface for search options."

        if any(w in text for w in ["task", "remind", "schedule", "todo"]):
            return "Task management is available. You can manage tasks through the web interface or tell me what you need scheduled."

        if any(w in text for w in ["run", "execute", "command", "terminal"]):
            return "System commands are available through the web interface dashboard. What specifically do you need executed?"

        if len(text) > 3:
            self.context.append(("user", user_input))
            if len(self.context) > 10:
                self.context = self.context[-10:]

        responses = [
            "Got it. Let me know if you need anything specific.",
            "Understood. What else can I help with?",
            "Noted. Is there something specific you'd like me to do?",
            "I hear you. Let me know how I can assist.",
            "Alright. What would you like me to focus on?",
        ]
        return random.choice(responses)


class LLMEngine:
    def __init__(self, model: str = "llama3"):
        self.model = os.getenv("LLM_MODEL", model)
        self._ollama = None
        self._llama = None
        self._init_error = None
        self.strict_prod = os.getenv("SATURDAY_STRICT_PROD", "false").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

        self.config = {}
        config_path = "core/config.json"
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    self.config = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load config for LLMEngine: {e}")

        def _env_flag(name: str) -> bool:
            return os.getenv(name, "false").strip().lower() in {"1", "true", "yes", "on"}

        ai_config = self.config.get("ai", {})
        self.use_llama_cpp = ai_config.get("use_llama_cpp", False) or _env_flag("SATURDAY_USE_LLAMA_CPP")
        self.model_path = ai_config.get("model_path", "models/llama-3-8b-instruct.Q4_K_M.gguf")
        self.n_ctx = ai_config.get("n_ctx", 2048)
        self.n_gpu_layers = ai_config.get("n_gpu_layers", 0)
        self.preload = self.strict_prod or os.getenv("SATURDAY_PRELOAD_LLM", "false").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

        self.use_ollama = ai_config.get("use_ollama", False) or _env_flag("SATURDAY_USE_OLLAMA")
        self.ollama_url = os.getenv("OLLAMA_URL") or ai_config.get("ollama_url", "http://localhost:11434/api/generate")
        self.ollama_model = os.getenv("OLLAMA_MODEL") or ai_config.get("ollama_model", "phi3")

        self._builtin = BuiltinBrain()
        self._use_builtin = not (self.use_llama_cpp or self.use_ollama)

        if self.preload:
            backend_ok = False
            if self.use_ollama and self._check_ollama():
                backend_ok = True
            if not backend_ok and self.use_llama_cpp:
                backend_ok = bool(self._get_llama_cpp())
            if not backend_ok and self.strict_prod:
                raise RuntimeError(self._init_error or "LLM backend is unavailable.")
            if backend_ok:
                self._use_builtin = False

        if self._use_builtin:
            logger.info("Using built-in conversational brain (no local LLM configured)")

    @property
    def available(self) -> bool:
        return True

    def _resolve_model_path(self) -> str:
        if os.path.exists(self.model_path):
            return self.model_path
        search_dirs = ["models"]
        extra = os.getenv("SATURDAY_MODELS_DIR", "").strip()
        if extra:
            search_dirs.insert(0, extra)
        for directory in search_dirs:
            base = Path(directory)
            if not base.is_dir():
                continue
            matches = sorted(base.glob("*.gguf"))
            if matches:
                logger.info("Auto-discovered GGUF model", model=str(matches[0]))
                return str(matches[0])
        return self.model_path

    def _get_llama_cpp(self):
        if self._llama is None:
            try:
                from llama_cpp import Llama

                model_path = self._resolve_model_path()
                if not os.path.exists(model_path):
                    self._init_error = f"Llama model file not found: {model_path}"
                    logger.warning(self._init_error)
                    self._use_builtin = True
                    return None

                self._llama = Llama(
                    model_path=model_path,
                    n_ctx=self.n_ctx,
                    n_gpu_layers=self.n_gpu_layers,
                    verbose=False,
                )
                self._init_error = None
                self._use_builtin = False
                logger.info("llama-cpp model loaded successfully", model=model_path)
            except ImportError:
                self._init_error = "llama-cpp-python is not installed."
                logger.warning(self._init_error)
                self._llama = False
                self._use_builtin = True
            except Exception as e:
                self._init_error = f"Failed to initialize llama-cpp: {e}"
                logger.warning(self._init_error)
                self._llama = False
                self._use_builtin = True
        return self._llama

    def _check_ollama(self) -> bool:
        try:
            import requests

            tags_url = self.ollama_url.replace("/api/generate", "/api/tags")
            response = requests.get(tags_url, timeout=2)
            if response.status_code != 200:
                raise RuntimeError(f"Ollama responded {response.status_code}")
            logger.info("Ollama backend reachable", model=self.ollama_model)
            return True
        except Exception as e:
            self._init_error = f"Ollama backend unavailable: {e}"
            logger.warning(self._init_error)
            return False

    async def _stream_ollama(self, prompt: str):
        import aiohttp

        payload = {
            "model": self.ollama_model,
            "prompt": f"{BuiltinBrain.PERSONALITY}\n\nUser: {prompt}\n\nSATURDAY:",
            "stream": True,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(self.ollama_url, json=payload, timeout=aiohttp.ClientTimeout(total=120)) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"Ollama returned {resp.status}")
                async for raw in resp.content:
                    if not raw:
                        continue
                    try:
                        data = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    token = data.get("response") or ""
                    if token:
                        yield token

    async def chat_stream(self, prompt: str):
        if self.use_ollama:
            try:
                async for token in self._stream_ollama(prompt):
                    yield token
                return
            except Exception as e:
                logger.warning("Ollama backend failed; falling back", error=str(e))
                self.use_ollama = False

        if self._use_builtin:
            response = self._builtin.respond(prompt)
            for word in response.split():
                yield word + " "
                await asyncio.sleep(0.02)
            return

        llama = self._get_llama_cpp()
        if not llama:
            response = self._builtin.respond(prompt)
            for word in response.split():
                yield word + " "
                await asyncio.sleep(0.02)
            return

        try:
            loop = asyncio.get_event_loop()

            def _run_llama():
                return llama.create_chat_completion(
                    messages=[
                        {
                            "role": "system",
                            "content": BuiltinBrain.PERSONALITY,
                        },
                        {"role": "user", "content": prompt},
                    ],
                    stream=True,
                )

            response = await loop.run_in_executor(None, _run_llama)
            for chunk in response:
                if "choices" in chunk and len(chunk["choices"]) > 0:
                    delta = chunk["choices"][0].get("delta", {})
                    if "content" in delta:
                        yield delta["content"]
            return
        except Exception as e:
            logger.error("Llama-cpp execution failure", error=str(e))
            response = self._builtin.respond(prompt)
            for word in response.split():
                yield word + " "
                await asyncio.sleep(0.02)

    async def chat(self, prompt: str) -> str:
        chunks = []
        async for chunk in self.chat_stream(prompt):
            chunks.append(chunk)
        return "".join(chunks).strip()
