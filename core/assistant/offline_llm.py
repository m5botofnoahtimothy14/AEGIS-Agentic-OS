from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any, AsyncGenerator

import structlog

logger = structlog.get_logger("SATURDAY.Assistant.OfflineAI")


class OfflineAIEngine:
    """Fully offline GGUF chat backend (OfflineAI/Phi-3 inspired).

    Wraps llama-cpp-python with automatic GGUF discovery inside the models
    folder (or an explicit path). Uses the Phi-3 chat-markup prompt format.
    Every heavy import is lazy so the module is safe to import in any
    environment.
    """

    def __init__(
        self,
        model_path: Any = None,
        model_dir: Any = "models",
        n_ctx: int = 4096,
        n_gpu_layers: int = 0,
        max_tokens: int = 256,
    ) -> None:
        self.n_ctx = int(n_ctx)
        self.n_gpu_layers = int(n_gpu_layers)
        self.max_tokens = int(max_tokens)
        self.model_path = self._discover(model_path, model_dir)
        self.available = bool(self.model_path) and os.path.exists(self.model_path)
        self._llama = None
        self._init_error = None
        if self.available:
            logger.info("OfflineAI model located", model=self.model_path)
        else:
            self._init_error = f"No GGUF model found under {model_dir}"

    def _discover(self, model_path: Any, model_dir: Any) -> str:
        if model_path and os.path.exists(str(model_path)):
            return str(model_path)
        base = Path(model_dir)
        if base.is_dir():
            matches = sorted(base.glob("*.gguf"))
            if matches:
                return str(matches[0])
        env_path = os.getenv("SATURDAY_MODELS_DIR", "").strip()
        if env_path and os.path.isdir(env_path):
            env_base = Path(env_path)
            matches = sorted(env_base.glob("*.gguf"))
            if matches:
                return str(matches[0])
        return str(model_path) if model_path else str(base / "model.gguf")

    def _get_llama(self):
        if self._llama is None:
            if not self.available:
                return None
            try:
                from llama_cpp import Llama

                self._llama = Llama(
                    model_path=self.model_path,
                    n_ctx=self.n_ctx,
                    n_gpu_layers=self.n_gpu_layers,
                    verbose=False,
                )
            except ImportError:
                self._init_error = "llama-cpp-python is not installed."
                logger.warning(self._init_error)
                self._llama = False
            except Exception as e:
                self._init_error = f"Failed to initialize llama-cpp: {e}"
                logger.warning(self._init_error)
                self._llama = False
        return self._llama if self._llama else None

    def generate(self, prompt: str, system: str = "") -> str:
        """Run a single non-streaming generation (OfflineAI-style console)."""
        llama = self._get_llama()
        if llama is None:
            return self._init_error or "OfflineAI backend is unavailable."
        full_prompt = ""
        if system:
            full_prompt += f"<|system|>\n{system}<|end|>\n"
        full_prompt += f"<|user|>\n{prompt}<|end|>\n<|assistant|>"
        try:
            output = llama(
                full_prompt,
                max_tokens=self.max_tokens,
                stop=["<|end|>"],
                echo=False,
            )
            return (output.get("choices") or [{}])[0].get("text", "").strip()
        except Exception as e:
            logger.error("OfflineAI generation failed", error=str(e))
            return f"I hit an error during local generation: {e}"

    async def chat_stream(self, prompt: str) -> AsyncGenerator[str, None]:
        if not self.available:
            yield self._init_error or "OfflineAI backend is unavailable."
            return
        loop = asyncio.get_event_loop()
        llama = self._get_llama()
        if llama is None:
            yield self._init_error or "OfflineAI backend is unavailable."
            return
        full_prompt = f"<|user|>\n{prompt}<|end|>\n<|assistant|>"

        def _run():
            return llama(full_prompt, max_tokens=self.max_tokens, stop=["<|end|>"], echo=False, stream=True)

        try:
            response = await loop.run_in_executor(None, _run)
            for chunk in response:
                delta = (chunk.get("choices") or [{}])[0].get("text", "")
                if delta:
                    yield delta
        except Exception as e:
            logger.error("OfflineAI stream failed", error=str(e))
            yield f"I hit an error during local generation: {e}"

    async def chat(self, prompt: str) -> str:
        chunks = []
        async for chunk in self.chat_stream(prompt):
            chunks.append(chunk)
        return "".join(chunks).strip()