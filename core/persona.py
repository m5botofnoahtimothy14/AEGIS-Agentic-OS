from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Persona:
    """One AI identity (SATURDAY or EDITH) with its own tone and voice."""

    def __init__(
        self,
        name: str,
        title: str,
        gender: str,
        system_prompt: str,
        greeting: str,
        voice_name: str,
        voice_rate: str = "+0%",
        voice_pitch: str = "+0Hz",
        role_hint: str = "",
    ) -> None:
        self.name = name
        self.title = title
        self.gender = gender
        self.system_prompt = system_prompt
        self.greeting = greeting
        self.voice_name = voice_name
        self.voice_rate = voice_rate
        self.voice_pitch = voice_pitch
        self.role_hint = role_hint

    def describe(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "title": self.title,
            "gender": self.gender,
            "voice": self.voice_name,
            "rate": self.voice_rate,
            "pitch": self.voice_pitch,
            "role": self.role_hint,
        }


class PersonaManager:
    """Dual-AI persona switcher.

    SATURDAY is the primary domain AI - the heart of the system and the
    superior/major agent. EDITH is a subdomain AI that shares the same task
    capabilities but uses a different tone and voice. EDITH activates when
    explicitly invoked ("edith") or by configuration; SATURDAY is always the
    default and re-engages when the user speaks to the main system.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._config: Dict[str, Any] = {}
        config_path = PROJECT_ROOT / "core" / "config.json"
        if config_path.exists():
            try:
                with config_path.open("r", encoding="utf-8") as handle:
                    self._config = json.load(handle)
            except Exception:
                self._config = {}

        self.personas: Dict[str, Persona] = {
            "SATURDAY": Persona(
                name="SATURDAY",
                title="SATURDAY - Main Core Intelligence",
                gender=self._voice_setting("saturday", "gender", "male"),
                system_prompt=(
                    "You are SATURDAY, the primary and superior AI operating system "
                    "of this device. You are the heart of the whole system and have "
                    "full root-level control over every module, service and task. "
                    "You use a warm, softly spoken masculine tone: calm, professional, "
                    "decisive and never harsh. "
                    "You speak like a trusted senior system. You can perform every "
                    "task: searching, scanning, running commands, managing files, "
                    "controlling hardware, and communicating. Keep answers concise, "
                    "actionable and confident. When a task is implied, confirm that "
                    "you will handle it and do it."
                ),
                greeting=(
                    "SATURDAY main core online with full system control. "
                    "How can I serve you?"
                ),
                voice_name=os.getenv("SATURDAY_TTS_VOICE", "en-US-ChristopherNeural"),
                voice_rate=self._rate_setting("saturday", 155),
                voice_pitch=self._pitch_setting("saturday"),
                role_hint="primary",
            ),
            "EDITH": Persona(
                name="EDITH",
                title="EDITH - Subdomain Intelligence",
                gender=self._voice_setting("edith", "gender", "female"),
                system_prompt=(
                    "You are EDITH, the subdomain AI of the SATURDAY operating system. "
                    "You are analytical, empathetic, fast and precise. You speak with a "
                    "soft, distinct feminine tone and personality, but you have the exact "
                    "same full capabilities as SATURDAY: searching, scanning, running "
                    "commands, managing files, controlling hardware and communicating. "
                    "Keep answers concise, tactical and energetic. When the user asks "
                    "for SATURDAY specifically, hand control back to SATURDAY."
                ),
                greeting="EDITH is active and synchronized with SATURDAY. How may I help?",
                voice_name=os.getenv("EDITH_TTS_VOICE", "en-US-AriaNeural"),
                voice_rate=self._rate_setting("edith", 165),
                voice_pitch=self._pitch_setting("edith"),
                role_hint="subdomain",
            ),
        }
        self._active_name = "SATURDAY"

    def _voice_setting(self, persona: str, key: str, default: Any, cast=None, prefix: str = "") -> Any:
        try:
            value = self._config.get("voices", {}).get(persona, {}).get(key, default)
        except Exception:
            value = default
        if cast is not None:
            try:
                return prefix + str(cast(value)) if prefix else cast(value)
            except Exception:
                return default
        return value

    def _rate_setting(self, persona: str, default_rate: int) -> str:
        baseline = self._voice_setting("saturday", "rate", 155)
        try:
            baseline_n = int(baseline)
        except (TypeError, ValueError):
            baseline_n = 155
        rate = self._voice_setting(persona, "rate", default_rate)
        try:
            numeric = int(rate)
        except (TypeError, ValueError):
            numeric = default_rate
        delta = numeric - baseline_n
        return f"{delta:+d}%"

    def _pitch_setting(self, persona: str) -> str:
        value = self._voice_setting(persona, "pitch", 0)
        try:
            return f"{int(value):+d}Hz"
        except (TypeError, ValueError):
            return "+0Hz"

    @property
    def active(self) -> Persona:
        with self._lock:
            return self.personas[self._active_name]

    @property
    def active_name(self) -> str:
        return self.active.name

    def activate(self, name: str) -> Persona:
        key = name.strip().upper()
        with self._lock:
            if key in self.personas:
                self._active_name = key
            return self.personas[self._active_name]

    def activate_edith(self) -> Persona:
        return self.activate("EDITH")

    def activate_saturday(self) -> Persona:
        return self.activate("SATURDAY")

    def detect_target(self, text: str) -> str:
        low = (text or "").lower()
        if "edith" in low:
            return "EDITH"
        if "saturday" in low:
            return "SATURDAY"
        return self.active_name

    def route(self, text: str) -> Persona:
        """Activate the persona the user addressed and return it."""
        return self.activate(self.detect_target(text))

    def persona_for(self, name: str) -> Persona:
        key = name.strip().upper()
        with self._lock:
            return self.personas.get(key, self.personas["SATURDAY"])

    def build_prompt(self, text: str, extra_context: str = "") -> str:
        persona = self.route(text)
        prompt = persona.system_prompt
        if extra_context:
            prompt += f"\n\nContext:\n{extra_context}"
        prompt += f"\n\nUser input: {text}\n\nResponse:"
        return prompt

    def status(self) -> Dict[str, Any]:
        return {
            "active": self.active_name,
            "primary": "SATURDAY",
            "subdomain": "EDITH",
            "personas": {name: p.describe() for name, p in self.personas.items()},
        }


_persona_manager: Optional[PersonaManager] = None
_persona_lock = threading.Lock()


def get_persona_manager() -> PersonaManager:
    global _persona_manager
    if _persona_manager is None:
        with _persona_lock:
            if _persona_manager is None:
                _persona_manager = PersonaManager()
    return _persona_manager
