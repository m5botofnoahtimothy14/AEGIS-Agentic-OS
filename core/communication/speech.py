import logging
import os
import queue
import threading
import time
import tempfile
import asyncio

import numpy as np

try:
    import sounddevice as sd
except (ImportError, OSError):
    sd = None

logger = logging.getLogger("SATURDAY.Speech")

EDGE_TTS_AVAILABLE = False
try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    pass

PIPER_AVAILABLE = False
try:
    from piper import PiperVoice
    PIPER_AVAILABLE = True
except ImportError:
    PiperVoice = None

SATURDAY_VOICE = os.getenv("SATURDAY_TTS_VOICE", "en-US-ChristopherNeural")
SATURDAY_VOICE_RATE = os.getenv("SATURDAY_TTS_RATE", "+0%")
SATURDAY_VOICE_PITCH = os.getenv("SATURDAY_TTS_PITCH", "+0Hz")
EDITH_VOICE = os.getenv("EDITH_TTS_VOICE", "en-US-AriaNeural")
EDITH_VOICE_RATE = os.getenv("EDITH_TTS_RATE", "+10%")
EDITH_VOICE_PITCH = os.getenv("EDITH_TTS_PITCH", "+0Hz")


class SpeechManager:
    def __init__(self):
        self._lock = threading.Lock()
        self.piper_voice = None
        self.backend = None
        self._queue = queue.Queue()
        self._speaker_thread = None
        self._init_backend()

    def _init_backend(self):
        if EDGE_TTS_AVAILABLE:
            self.backend = "edge-tts"
            self._speaker_thread = threading.Thread(target=self._speaker_loop, daemon=True)
            self._speaker_thread.start()
            logger.info(f"TTS backend: Edge TTS (voice={SATURDAY_VOICE})")
            return

        self._init_piper()
        if self.piper_voice:
            self.backend = "piper"
            self._speaker_thread = threading.Thread(target=self._speaker_loop, daemon=True)
            self._speaker_thread.start()
            logger.info("TTS backend: Piper (single-voice fallback)")
            return

        self._speaker_thread = threading.Thread(target=self._speaker_loop, daemon=True)
        self._speaker_thread.start()
        if sd:
            self.backend = "sounddevice"
            logger.info("TTS backend: SoundDevice (cross-platform)")
        else:
            self.backend = "none"
            logger.warning("No TTS backend available")

    def _init_piper(self):
        if not PIPER_AVAILABLE:
            return False
        model_path = os.getenv("PIPER_MODEL_PATH", "models/piper/en_US-lessac-medium.onnx")
        if not model_path or not os.path.exists(model_path):
            return False
        try:
            config_path = model_path.replace(".onnx", ".onnx.json")
            if not os.path.exists(config_path):
                config_path = model_path.replace(".onnx", ".json")
            self.piper_voice = PiperVoice.load(model_path, config_path=config_path)
            logger.info(f"Piper loaded: {model_path}")
            return True
        except Exception as e:
            logger.error(f"Piper init failed: {e}")
            return False

    @property
    def available(self) -> bool:
        return self.piper_voice is not None or self.backend == "edge-tts" or sd is not None

    def speak(self, text: str, lang_hint: str = None, persona: str = None):
        if not text:
            return
        if self._queue.qsize() > 10:
            return
        self._queue.put((text, lang_hint, persona))

    def _speaker_loop(self):
        while True:
            try:
                text, lang_hint, persona = self._queue.get()
                with self._lock:
                    persona = self._resolve_persona(text, persona)
                    spoken_text = self._spoken_text(text)
                    if self.backend == "piper" and self.piper_voice:
                        self._speak_piper(spoken_text)
                    elif self.backend == "edge-tts":
                        self._speak_edge(spoken_text, persona)
                    else:
                        self._speak_fallback(spoken_text)
            except Exception as e:
                logger.warning(f"Speech error: {e}")

    def _resolve_persona(self, text: str, requested_persona: str = None) -> str:
        if requested_persona:
            return str(requested_persona).upper()
        if str(text).lstrip().upper().startswith("EDITH:"):
            return "EDITH"
        try:
            from core.persona import get_persona_manager
            return get_persona_manager().active_name
        except Exception:
            return "SATURDAY"

    @staticmethod
    def _spoken_text(text: str) -> str:
        """Keep persona labels for UI/event logs but do not say them aloud."""
        for label in ("SATURDAY:", "EDITH:"):
            if str(text).lstrip().upper().startswith(label):
                return str(text).lstrip()[len(label):].lstrip()
        return str(text)

    def _speak_edge(self, text: str, persona: str = "SATURDAY"):
        try:
            tmp_path = os.path.join(tempfile.gettempdir(), "saturday_speech.mp3")
            defaults = (EDITH_VOICE, EDITH_VOICE_RATE, EDITH_VOICE_PITCH) if persona == "EDITH" else (
                SATURDAY_VOICE, SATURDAY_VOICE_RATE, SATURDAY_VOICE_PITCH
            )
            try:
                from core.persona import get_persona_manager
                profile = get_persona_manager().persona_for(persona)
                voice, rate, pitch = profile.voice_name, profile.voice_rate, profile.voice_pitch
            except Exception:
                voice, rate, pitch = defaults
            communicate = edge_tts.Communicate(
                text,
                voice,
                rate=rate,
                pitch=pitch,
            )
            asyncio.run(communicate.save(tmp_path))

            if os.path.exists(tmp_path) and sd:
                try:
                    import miniaudio
                    decoded = miniaudio.decode_file(tmp_path, output_format=miniaudio.SampleFormat.FLOAT32)
                    # decoded.samples is flat interleaved; reshape to (frames, channels)
                    audio_data = np.asarray(decoded.samples, dtype=np.float32)
                    if decoded.nchannels > 1:
                        try:
                            audio_data = audio_data.reshape(-1, decoded.nchannels)
                        except Exception:
                            pass
                        # Play stereo directly if 2ch, or mix to mono
                        # sounddevice handles (frames, channels) - keep as 2D for stereo
                        if audio_data.ndim == 2 and audio_data.shape[1] == 2:
                            # Keep stereo - sounddevice will play correctly
                            pass
                        elif audio_data.ndim == 2:
                            audio_data = audio_data.mean(axis=1)
                    sd.play(audio_data, decoded.sample_rate)
                    sd.wait()
                except Exception:
                    try:
                        self._speak_fallback(text)
                    except Exception:
                        pass
                finally:
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass
            elif os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"Edge TTS error: {e}")
            self._speak_fallback(text)

    def _speak_piper(self, text: str):
        if not self.piper_voice or not sd:
            self._speak_fallback(text)
            return
        try:
            wav_path = os.path.join(tempfile.gettempdir(), "saturday_piper.wav")
            self.piper_voice.synthesize_wav(text, wav_path)
            if os.path.exists(wav_path):
                audio_data, sr = self._load_wav(wav_path)
                sd.play(audio_data, sr)
                sd.wait()
                try:
                    os.remove(wav_path)
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Piper error: {e}")
            self._speak_fallback(text)

    def _speak_fallback(self, text: str):
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty("rate", 155)
            engine.setProperty("volume", 1.0)
            engine.say(text)
            engine.runAndWait()
            return
        except Exception:
            pass
        logger.info(f"TTS unavailable (text only): {text[:80]}...")

    def _load_wav(self, filepath: str):
        import wave
        with wave.open(filepath, "rb") as wf:
            sr = wf.getframerate()
            data = wf.readframes(-1)
            audio = np.frombuffer(data, dtype=np.int16)
            return audio, sr
