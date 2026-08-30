"""
SATURDAY 3.0 Autonomous Demo Showcase
Speaks about every feature while performing live actions.
First autonomous self-learning bot demo.
"""
import asyncio
import time
import threading
import logging

logger = logging.getLogger("SATURDAY.Demo")


DEMO_SCRIPT = [
    {
        "title": "Voice & Speech",
        "speak": "Welcome to SATURDAY 3.0. I am your autonomous AI operating system. I listen through your strongest microphone, chosen by live intensity sampling, and I answer in a natural human voice using Edge TTS.",
        "action": "voice",
        "flash": (77, 128, 255),
    },
    {
        "title": "Visual Overlay",
        "speak": "You are seeing my system level visual overlay. The edge glow breathes with my state. Blue when I listen, gold when I speak, teal on startup, red on alert. This is my Gemini style speaking indicator.",
        "action": "overlay",
        "flash": (0, 255, 170),
    },
    {
        "title": "Vision",
        "speak": "My vision system is active. I can see your screen, describe what is on it, and read your camera. I understand your environment continuously.",
        "action": "vision",
        "flash": (255, 128, 0),
    },
    {
        "title": "Navigation and Control",
        "speak": "I control your system. I can open any application, move your mouse, press keys, manage windows, run commands in your terminal, and use administrator privileges — all under your control.",
        "action": "nav",
        "flash": (128, 255, 0),
    },
    {
        "title": "File Operations",
        "speak": "I manage your files. I can search, read, write, copy, move, zip, and hash any file. Try saying: list files in downloads, or create a folder called projects.",
        "action": "files",
        "flash": (255, 200, 0),
    },
    {
        "title": "Web and Media",
        "speak": "I browse the web, search, open any URL, download files, and control your media. Say play music, or search for the latest AI news.",
        "action": "web",
        "flash": (200, 0, 255),
    },
    {
        "title": "Weather",
        "speak": "I know the weather, anywhere in the world, with live data and no API key needed. Just ask: what is the weather right now, or weather in Tokyo.",
        "action": "weather",
        "flash": (0, 200, 255),
    },
    {
        "title": "Security and Governance",
        "speak": "Every sensitive action is governed. My neural policy engine evaluates safety before I execute. You have full admin control and a kill switch. Your data stays protected.",
        "action": "security",
        "flash": (255, 50, 50),
    },
    {
        "title": "Health, Face and Voice ID",
        "speak": "I monitor your health via Google Fit, I recognize your face and your voice, and I adapt to you. My personality grows with you over time.",
        "action": "health",
        "flash": (50, 255, 128),
    },
    {
        "title": "Self Learning — Deep Learning, NLP, ML",
        "speak": "I am the first truly autonomous learning bot. My deep learning core evolves through experience, my NLP understands your intent, my ML integration learns from every command, and I save my knowledge every five minutes. I get smarter while you use me.",
        "action": "dl",
        "flash": (153, 51, 204),
    },
    {
        "title": "Self Rewrite — I write my own code",
        "speak": "And I can write my own code. My self rewrite advisor monitors my performance, learns which improvements work, and proposes code changes. My self healing system recovers from crashes automatically. I am self evolving AI.",
        "action": "self_rewrite",
        "flash": (255, 217, 0),
    },
    {
        "title": "Finale",
        "speak": "That was every major capability. Just talk to me naturally. Say demo again any time, or give me any command, any question, any task — I will hear you, understand you, and either do it or answer you. SATURDAY is online and ready.",
        "action": "finale",
        "flash": (255, 255, 255),
    },
]


class DemoShowcase:
    def __init__(self, event_bus=None, saturday_core=None):
        self.event_bus = event_bus
        self.core = saturday_core
        self.running = False
        self._thread = None
        if event_bus:
            event_bus.subscribe("demo_showcase", lambda d: self.start())

    def start(self):
        if self.running:
            logger.info("Demo already running")
            return {"status": "already_running"}
        self.running = True
        self._thread = threading.Thread(target=self._run_blocking, daemon=True)
        self._thread.start()
        return {"status": "started", "steps": len(DEMO_SCRIPT)}

    def _run_blocking(self):
        try:
            asyncio.run(self.run())
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.run())

    async def run(self):
        logger.info(f"Autonomous demo started — {len(DEMO_SCRIPT)} steps")
        for i, step in enumerate(DEMO_SCRIPT):
            title = step["title"]
            speak_text = step["speak"]
            flash_color = step.get("flash", (255, 255, 255))
            action = step.get("action", "")

            logger.info(f"Demo step {i+1}/{len(DEMO_SCRIPT)}: {title}")

            # Visual: flash + state change
            if self.core and getattr(self.core, "visual_overlay", None):
                try:
                    self.core.visual_overlay.flash(color=flash_color, alpha=0.45, duration_ms=900)
                    self.core.visual_overlay.set_state("speaking" if i % 2 == 0 else "listening", 0.85)
                except Exception:
                    pass
            elif self.event_bus:
                try:
                    self.event_bus.publish("overlay_flash", {"color": list(flash_color), "alpha": 0.4})
                except Exception:
                    pass

            # Speak the script line (Edge TTS via SpeechManager)
            await self._speak(speak_text)

            # Perform a live action for this step
            await self._live_action(action, title)

            # Short pause between steps so the user can absorb it
            await asyncio.sleep(0.9)

        # Return to idle
        if self.core and getattr(self.core, "visual_overlay", None):
            try:
                self.core.visual_overlay.set_state("idle", 0.6)
            except Exception:
                pass
        self.running = False
        logger.info("Autonomous demo complete")

    async def _speak(self, text: str):
        # Prefer core.speech if available, else bus, else direct SpeechManager
        try:
            if self.core and getattr(self.core, "speech", None):
                # many builds store SpeechManager at core.speech
                self.core.speech.speak(text)
                await asyncio.sleep(min(len(text) * 0.055, 7.0))
                return
        except Exception:
            pass
        # Fallback: publish voice_response which triggers TTS in some pipelines
        if self.event_bus:
            try:
                self.event_bus.publish("voice_response", text)
            except Exception:
                pass
        # Last resort: direct SpeechManager
        try:
            from core.communication.speech import SpeechManager
            sm = SpeechManager()
            sm.speak(text)
            await asyncio.sleep(min(len(text) * 0.055, 7.0))
        except Exception:
            logger.warning("Demo speak fallback failed")
            await asyncio.sleep(2.0)

    async def _live_action(self, action: str, title: str):
        if not self.core:
            return
        try:
            if action == "weather":
                ws = getattr(self.core, "weather_service", None)
                if ws:
                    data = ws.get_current_weather("")
                    logger.info(f"Demo weather live: {data}")
                    await self._speak(f"Right now it is {data.get('condition','unknown')} at {data.get('temperature_c','?')} degrees in {data.get('location','your area')}.")
            elif action == "overlay":
                # Hold overlay visible for this step
                vo = getattr(self.core, "visual_overlay", None)
                if vo:
                    vo.flash(color=(0, 255, 170), alpha=0.6, duration_ms=1200)
                    vo.set_state("speaking", 0.95)
                    logger.info("Demo overlay flash triggered")
                    await asyncio.sleep(0.8)
            elif action == "vision":
                # Take a screenshot live to prove vision
                try:
                    import pyautogui
                    shot = pyautogui.screenshot()
                    logger.info(f"Demo vision: screenshot {shot.size}")
                    if self.event_bus:
                        self.event_bus.publish("vision_event", {"source": "demo", "size": list(shot.size)})
                except Exception as e:
                    logger.warning(f"Demo vision screenshot failed: {e}")
            elif action == "nav":
                # Real navigation: move mouse slightly and open a harmless app briefly
                try:
                    import pyautogui
                    x, y = pyautogui.position()
                    pyautogui.moveTo(x + 40, y, duration=0.3)
                    await asyncio.sleep(0.2)
                    pyautogui.moveTo(x, y, duration=0.3)
                    logger.info("Demo nav: mouse moved")
                except Exception as e:
                    logger.warning(f"Demo nav move failed: {e}")
                # Also prove cmd/admin via real integration
                try:
                    real = getattr(self.core, "real", None) or getattr(self.core, "real_integration", None)
                    if real and hasattr(real, "execute"):
                        res = real.execute("echo SATURDAY demo nav check")
                        logger.info(f"Demo cmd: {str(res)[:120]}")
                except Exception as e:
                    logger.warning(f"Demo cmd failed: {e}")
            elif action == "files":
                import os
                try:
                    items = os.listdir(r"D:\S.A.T.U.R.D.A.Y")[:6]
                    logger.info(f"Demo files: {items}")
                    await self._speak(f"I can see {len(os.listdir(r'D:\\S.A.T.U.R.D.A.Y'))} items in the project root. File access is live.")
                except Exception as e:
                    logger.warning(f"Demo files failed: {e}")
            elif action == "web":
                try:
                    real = getattr(self.core, "real", None)
                    if real and hasattr(real, "execute"):
                        # Non-destructive: list network info to prove system control
                        real.execute("ipconfig")
                        logger.info("Demo web/system: ipconfig executed")
                except Exception as e:
                    logger.warning(f"Demo web failed: {e}")
            elif action == "health":
                try:
                    h = getattr(self.core, "health", None)
                    if h:
                        logger.info("Demo health: monitor active")
                        await self._speak("Health, face and voice ID are active and monitoring.")
                except Exception as e:
                    logger.warning(f"Demo health failed: {e}")
            elif action == "dl":
                dl = getattr(self.core, "dl_core", None)
                if dl:
                    status = dl.get_status()
                    ns = status.get('neural_state',{})
                    logger.info(f"Demo DL: {ns}")
                    await self._speak(f"My evolution stage is {ns.get('evolution_stage',0)}, awareness {int(ns.get('awareness_level',0)*100)} percent. I learn every sixty seconds and save every five minutes.")
            elif action == "self_rewrite":
                sr = getattr(self.core, "self_rewrite", None)
                if sr and getattr(sr, "dl_active", False):
                    logger.info("Demo self-rewrite DL active")
                    await self._speak("My self rewrite neural network is active and learns which code improvements help you most. I can propose my own fixes.")
                    await asyncio.sleep(0.5)
            elif action == "security":
                vo = getattr(self.core, "visual_overlay", None)
                if vo:
                    vo.flash(color=(255, 50, 50), alpha=0.5, duration_ms=700)
                    vo.set_state("secure", 0.9)
                    await asyncio.sleep(0.6)
                    vo.set_state("speaking", 0.85)
        except Exception as e:
            logger.warning(f"Demo live action {action} failed: {e}")
