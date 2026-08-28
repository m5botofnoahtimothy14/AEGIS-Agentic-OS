#!/usr/bin/env python3
"""
SATURDAY 3.0 -- System-level Visual Overlay (standalone)
Transparent fullscreen topmost window with animated edge glow,
screen flash, and AI state indicators.
Can be run as:  python visual_overlay.py            (standalone demo)
                python visual_overlay.py --watch     (reads commands from a file)
"""
import logging
import math
import sys
import os
import json
import threading
import time
import tkinter as tk
from tkinter import Canvas
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("SATURDAY.VisualOverlay")

STATE_COLORS = {
    "idle":      (255, 179, 0),
    "listening": (77, 128, 255),
    "speaking":  (255, 217, 0),
    "secure":    (153, 51, 204),
    "transfer":  (0, 255, 255),
    "alert":     (255, 50, 50),
    "startup":   (0, 255, 170),
}

CMD_FILE = os.path.join(os.environ.get("TEMP", os.getcwd()), "saturday_overlay_cmds.txt")


class VisualOverlay:
    def __init__(self):
        self._root = None
        self._canvas = None
        self._running = False
        self._state = "startup"
        self._color = STATE_COLORS["startup"]
        self._intensity = 0.8
        self._flash_alpha = 0.0
        self._flash_color = (255, 255, 255)
        self._breath_phase = 0.0
        self._pulse_phase = 0.0
        self._time = 0.0
        self._glow_items = []
        self._flash_item = None
        self._center_orb = None
        self._speaking_bars = []
        self._width = 1920
        self._height = 1080
        self._border_width = 80

    def start(self):
        self._root = tk.Tk()
        self._root.withdraw()
        self._root.after(50, self._setup_window)
        self._running = True
        self._root.mainloop()

    def set_state(self, state: str, intensity: float = None):
        self._state = state
        if state in STATE_COLORS:
            self._color = STATE_COLORS[state]
        if intensity is not None:
            self._intensity = max(0.1, min(1.0, intensity))

    def flash(self, color=(255, 255, 255), alpha=0.7, duration_ms=300):
        self._flash_color = color
        self._flash_alpha = alpha
        if self._root:
            self._root.after(int(duration_ms), self._clear_flash)

    def _clear_flash(self):
        self._flash_alpha = 0.0

    def _setup_window(self):
        root = self._root
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        self._width, self._height = sw, sh
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.attributes("-alpha", 1.0)
        root.configure(bg="black")
        root.geometry(f"{sw}x{sh}+0+0")
        try:
            import ctypes
            root.update_idletasks()
            hwnd = root.winfo_id()
            GWL_EXSTYLE, WS_EX_LAYERED, WS_EX_TRANSPARENT, WS_EX_TOOLWINDOW = -20, 0x00080000, 0x00000020, 0x00000080
            s = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, s | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW)
            root.attributes("-transparentcolor", "black")
            logger.info(f"Overlay ready {sw}x{sh} HWND={hwnd}")
        except Exception as e:
            logger.warning(f"Click-through setup: {e}")
            try:
                root.attributes("-transparentcolor", "black")
            except Exception:
                pass

        self._canvas = Canvas(root, width=sw, height=sh, bg="black", highlightthickness=0)
        self._canvas.pack()
        for i in range(6):
            item = self._canvas.create_rectangle(0, 0, 1, 1, outline="", width=0)
            self._glow_items.append((item, 1.0 - i / 6.0))
        self._flash_item = self._canvas.create_rectangle(0, 0, sw, sh, fill="", outline="")
        cx, cy = sw // 2, sh // 2
        self._center_orb = self._canvas.create_oval(cx - 60, cy - 60, cx + 60, cy + 60, fill="", outline="")
        bar_w, bar_gap, n_bars = 4, 6, 12
        total_w = n_bars * bar_w + (n_bars - 1) * bar_gap
        sx = cx - total_w // 2
        by = sh - 100
        self._speaking_bars = []
        for i in range(n_bars):
            x = sx + i * (bar_w + bar_gap)
            item = self._canvas.create_rectangle(x, by, x + bar_w, by + 20, fill="", outline="")
            self._speaking_bars.append(item)
        self._animate()

    def _animate(self):
        if not self._running or not self._canvas:
            return
        dt = 0.033
        self._time += dt
        self._breath_phase += dt * 1.5
        self._pulse_phase += dt * 3.0
        self._draw_glow()
        self._draw_flash()
        self._draw_orb()
        self._draw_bars()
        if self._flash_alpha > 0:
            self._flash_alpha = max(0, self._flash_alpha - dt * 1.5)
        self._root.after(33, self._animate)

    def _draw_glow(self):
        c, w, h, bw = self._canvas, self._width, self._height, self._border_width
        r, g, b = self._color
        t = self._time
        intensity = self._intensity * (0.7 + 0.3 * math.sin(self._breath_phase)) * (0.85 + 0.15 * math.sin(self._pulse_phase))
        for idx, (item, af) in enumerate(self._glow_items):
            off = int(idx * (bw / 6) * intensity)
            wv = math.sin(t * 1.2 + idx * 0.5) * 3 + math.sin(t * 0.8 + idx * 0.3) * 2
            fade = af * intensity
            cr, cg, cb = min(255, int(r * fade)), min(255, int(g * fade)), min(255, int(b * fade))
            lw = max(1, int((bw / 6) * fade * 1.5))
            c.coords(item, off + wv, off + wv, w - off - wv, h - off - wv)
            c.itemconfig(item, outline=f"#{cr:02x}{cg:02x}{cb:02x}", width=lw)
        if self._glow_items:
            ci = self._glow_items[0][0]
            ccr, ccg, ccb = min(255, int(r * 0.5 + 128)), min(255, int(g * 0.5 + 128)), min(255, int(b * 0.5 + 128))
            c.itemconfig(ci, width=max(1, int(2 * intensity)), outline=f"#{ccr:02x}{ccg:02x}{ccb:02x}")

    def _draw_flash(self):
        c = self._canvas
        if self._flash_alpha <= 0.01:
            c.itemconfig(self._flash_item, fill="", outline="")
            return
        r, g, b = self._flash_color
        br, bg, bb = int(r * self._flash_alpha), int(g * self._flash_alpha), int(b * self._flash_alpha)
        c.coords(self._flash_item, 0, 0, self._width, self._height)
        c.itemconfig(self._flash_item, fill=f"#{br:02x}{bg:02x}{bb:02x}", outline="")

    def _draw_orb(self):
        c, cx, cy = self._canvas, self._width // 2, self._height // 2
        r, g, b, t = *self._color, self._time
        br = 40 + int(20 * abs(math.sin(t * 3))) if self._state in ("speaking", "listening") else 35 + int(5 * math.sin(t * 0.5))
        gr = br + 25
        f = 0.4 * self._intensity
        c.coords(self._center_orb, cx - gr, cy - gr, cx + gr, cy + gr)
        c.itemconfig(self._center_orb, fill=f"#{min(255, int(r * f)):02x}{min(255, int(g * f)):02x}{min(255, int(b * f)):02x}", outline="")

    def _draw_bars(self):
        c, t, r, g, b = self._canvas, self._time, *self._color
        active = self._state in ("speaking", "listening")
        bar_w, bar_gap, n_bars = 4, 6, 12
        total_w = n_bars * bar_w + (n_bars - 1) * bar_gap
        for i, item in enumerate(self._speaking_bars):
            if active:
                ph = t * 4.0 + i * 0.5
                ht = int(10 + 25 * abs(math.sin(ph)) * (0.5 + 0.5 * math.sin(t * 1.5 + i)))
                x = self._width // 2 - total_w // 2 + i * (bar_w + bar_gap)
                by = self._height - 100
                f = 0.6 + 0.4 * math.sin(ph)
                c.coords(item, x, by - ht, x + bar_w, by)
                c.itemconfig(item, fill=f"#{min(255, int(r * f)):02x}{min(255, int(g * f)):02x}{min(255, int(b * f)):02x}", outline="")
            else:
                c.itemconfig(item, fill="", outline="")


def _watch_commands(overlay):
    """Watch a command file and apply state/flash commands."""
    last_pos = 0
    import time as _t
    while True:
        try:
            if os.path.exists(CMD_FILE):
                with open(CMD_FILE, "r") as fh:
                    fh.seek(last_pos)
                    lines = fh.readlines()
                    last_pos = fh.tell() if lines else last_pos
                    for line in lines:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        try:
                            cmd = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        action = cmd.get("action", "")
                        if action == "state":
                            overlay.set_state(cmd.get("state", "idle"), cmd.get("intensity"))
                        elif action == "flash":
                            overlay.flash(tuple(cmd.get("color", [255, 255, 255])), cmd.get("alpha", 0.7), cmd.get("duration_ms", 300))
                        elif action == "quit":
                            overlay._running = False
                            if overlay._root:
                                overlay._root.after(0, overlay._root.destroy)
                            return
            _t.sleep(0.2)
        except Exception:
            _t.sleep(0.5)


if __name__ == "__main__":
    overlay = VisualOverlay()
    cthread = threading.Thread(target=_watch_commands, args=(overlay,), daemon=True)
    cthread.start()
    logger.info("SATURDAY visual overlay starting...")
    overlay.start()


class VisualOverlayManager:
    """Launches the overlay as a self-invoked child process and controls it
    via a shared command file. Works in both source and frozen modes."""

    def __init__(self, event_bus=None):
        self._proc = None
        self._cmd_file = CMD_FILE
        self._app_state = "idle"
        if event_bus:
            event_bus.subscribe("voice_response", lambda t: self.set_state("speaking", 0.9))
            event_bus.subscribe("voice_response", lambda t: self.flash((255, 217, 0), 0.3, 500))
            event_bus.subscribe("voice_command", lambda d: self.set_state("listening", 0.7))
            event_bus.subscribe("voice_command", lambda d: self.flash((77, 128, 255), 0.25, 400))
            event_bus.subscribe("security_alert", lambda d: self.flash((255, 50, 50), 0.6, 600))
            event_bus.subscribe("security_alert", lambda d: self.set_state("alert", 1.0))

    def start(self):
        try:
            import subprocess
            exe = sys.executable
            if not exe or not os.path.exists(exe):
                logger.warning("Cannot locate interpreter for overlay")
                return
            cmd = [exe, "--overlay-child"]
            logger.info(f"Launching visual overlay child: {exe}")
            self._proc = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            logger.info("Visual overlay child process spawned")
        except Exception as e:
            logger.warning(f"Overlay launch failed: {e}")

    def _write(self, cmd: dict):
        try:
            with open(self._cmd_file, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(cmd) + "\n")
        except Exception:
            pass

    def set_state(self, state: str, intensity: float = None):
        self._app_state = state
        cmd = {"action": "state", "state": state}
        if intensity is not None:
            cmd["intensity"] = intensity
        self._write(cmd)

    def flash(self, color=(255, 255, 255), alpha=0.7, duration_ms=300):
        self._write({"action": "flash", "color": list(color), "alpha": alpha, "duration_ms": duration_ms})

    def stop(self):
        try:
            if self._proc and self._proc.poll() is None:
                self._write({"action": "quit"})
                self._proc.wait(timeout=3)
        except Exception:
            pass
        self._proc = None