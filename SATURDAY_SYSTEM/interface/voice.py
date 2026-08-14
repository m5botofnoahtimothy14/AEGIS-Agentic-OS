import logging

logger = logging.getLogger("SATURDAY.Voice")

class SATURDAYVoice:
    """
    SATURDAY Voice Interface Module.
    This serves as a bridge for STT (Speech-to-Text) and TTS (Text-to-Speech) engines.
    """
    def __init__(self, core):
        self.core = core
        self.active = False

    def start_listening(self):
        """
        In a full implementation, this would initialize a microphone 
        and run a local STT engine (like Whisper.cpp or Vosk).
        """
        logger.info("Voice engine initialized. (Simulated)")
        self.active = True

    def stop_listening(self):
        self.active = False
        logger.info("Voice engine suspended.")

    def process_voice_command(self, audio_data):
        """Processes audio and passes transcribed text to SATURDAY core."""
        # Simulated transcription
        transcription = "status"
        logger.info(f"Transcribed: {transcription}")
        return self.core.process_command(transcription)

    def speak(self, text: str):
        """Outputs text through local TTS engine (like Piper or Coqui)."""
        logger.info(f"SATURDAY Speaking: {text}")
        try:
            import os
            if os.getenv("SATURDAY_TTS", "piper").lower() == "piper":
                import shutil
                import subprocess
                import tempfile
                piper = shutil.which("piper")
                if piper:
                    model = os.getenv("PIPER_MODEL_PATH", "")
                    if model and os.path.exists(model):
                        tmp_wav = os.path.join(tempfile.gettempdir(), "saturday_tts.wav")
                        subprocess.run(
                            ["piper", "--model", model, "--output_file", tmp_wav],
                            input=text, capture_output=True, text=True, check=True,
                        )
                        player = shutil.which("aplay") or shutil.which("afplay") or shutil.which("play")
                        if player:
                            subprocess.Popen([player, tmp_wav])
                        return
                    raise FileNotFoundError("Piper model not found")
            try:
                import subprocess
                tts_cli = os.getenv("SATURDAY_TTS_CLI")
                if tts_cli and os.path.exists(tts_cli):
                    subprocess.run([tts_cli, text], check=True)
                    return
            except Exception:
                pass
            # Fallback: platform text-to-speech
            import sys
            if sys.platform == "darwin":
                import subprocess
                subprocess.Popen(["say", text])
            elif sys.platform.startswith("win"):
                import winsound
                winsound.MessageBeep()
            else:
                self._fallback_voice(text)
        except Exception as e:
            logger.error(f"TTS failed: {e}")

    def _fallback_voice(self, text: str):
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            logger.warning(f"No local TTS engine available: {e}")
