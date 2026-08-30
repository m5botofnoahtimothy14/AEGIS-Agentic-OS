# SATURDAY HomeBot - self-contained firmware (flattened for single-file deploy).

# ==== ui/eye_engine.py ====
# SATURDAY HomeBot - procedural animated eye engine (M5Stack Core2).
# Draws two expressive eyes with smooth interpolation, natural blinking,
# idle wandering and transient behaviors. Pure graphics, no voice logic.

import time
import math

try:
    import M5
    from M5 import *
except ImportError:
    M5 = None


def _now():
    try:
        return time.ticks_ms()
    except Exception:
        return int(time.time() * 1000)


def _diff(a, b):
    try:
        return time.ticks_diff(a, b)
    except Exception:
        return a - b


# ---- shared parameter schema (consumed by expression_engine.py) ----
# Numeric keys are interpolated smoothly by AnimationController.
NUM_KEYS = [
    "open_l", "open_r",
    "plx", "ply", "prx", "pry",
    "iris_l", "iris_r",
    "brow_l_lift", "brow_l_tilt", "brow_r_lift", "brow_r_tilt",
    "mouth_w",
]
# Categorical keys switch instantly (no interpolation).
CAT_KEYS = ["happy", "blink", "idle", "speaking", "cross", "think", "mouth", "accent"]

DEFAULT_PARAMS = {
    "open_l": 1.0, "open_r": 1.0,
    "plx": 0.0, "ply": 0.0, "prx": 0.0, "pry": 0.0,
    "iris_l": 1.0, "iris_r": 1.0,
    "brow_l_lift": 0.0, "brow_l_tilt": 0.0,
    "brow_r_lift": 0.0, "brow_r_tilt": 0.0,
    "mouth_w": 0.0,
    "happy": 0, "blink": 1, "idle": 1, "speaking": 0,
    "cross": 0, "think": 0, "mouth": 1, "accent": 0,
}

BG = 0x10131A
SCLERA = 0xF4F6F8
IRIS = 0x4A7DFF
IRIS_HI = 0x8FADFF
PUPIL = 0x0B0E14
LID = BG
OUTLINE = 0x2A3340
LID_LINE = 0x5A6B7E
MOUTH = 0xE7E9ED
ACC_LISTEN = 0x3DF0A8
ACC_ALERT = 0xFF5D5D
ACC_ERROR = 0xFF3B30
ACC_THINK = 0x7FD0FF


class EyeEngine:
    """Procedural, smoothly animated two-eye face for SATURDAY HomeBot."""

    def __init__(self, w=320, h=240):
        self.w = w
        self.h = h
        self.p = dict(DEFAULT_PARAMS)
        self.g = None
        self.use_canvas = False
        rx = int(min(w * 0.27, h * 0.30))
        cy = int(h * 0.42)
        self.eyes = [
            [int(w * 0.28), cy, rx],
            [int(w * 0.72), cy, rx],
        ]
        self.now = 0
        self._seed = 0x12345678
        self.blink_mult = 1.0
        self.blink_state = 0
        self.blink_t0 = 0
        self.blink_duration = 120
        self.next_blink = 1500
        self.blink_again = 0
        self.wander_x = 0.0
        self.wander_y = 0.0
        self.wander_tx = 0.0
        self.wander_ty = 0.0
        self.wander_t = 0
        self.glance_x = 0.0
        self.glance_y = 0.0
        self.glance_until = 0
        self.bounce_y = 0.0
        self.bounce_until = 0
        self.tilt_x = 0.0
        self.tilt_until = 0
        self.alert_until = 0
        self.asleep = False
        self.saccade_x = 0.0
        self.saccade_y = 0.0
        self.saccade_tx = 0.0
        self.saccade_ty = 0.0
        self.saccade_t = 0
        self.status_text = None
        self.mqtt_state = "disconnected"
        self.status_color = 0xFFFFFF

    # ---------- lifecycle ----------
    def begin(self):
        self._seed = (_now() ^ 0x9E3779B9) & 0xFFFFFFFF
        self.g = None
        self.use_canvas = False
        try:
            c = M5.Lcd.newCanvas(self.w, self.h, 16, True)
            if c is not None:
                self.g = c
                self.use_canvas = True
        except Exception:
            pass
        if self.g is None:
            self.g = M5.Lcd
            self.use_canvas = False
        try:
            self.g.setFont(M5.Lcd.FONTS.Montserrat12)
        except Exception:
            pass
        self.set_params(DEFAULT_PARAMS)
        self.update(0)

    def set_params(self, params):
        if params is not None:
            self.p = params

    def set_status(self, state_text, mqtt_state="disconnected", color=0xFFFFFF):
        self.status_text = state_text
        self.mqtt_state = mqtt_state
        self.status_color = color

    # ---------- commands / behaviors ----------
    def command(self, name):
        n = str(name).lower()
        if n == "look_left":
            self._glance(-0.85, 0.0, 700)
        elif n == "look_right":
            self._glance(0.85, 0.0, 700)
        elif n == "look_up":
            self._glance(0.0, -0.7, 700)
        elif n == "look_down":
            self._glance(0.0, 0.7, 700)
        elif n == "blink":
            self._trigger_blink(1)
        elif n == "double_blink":
            self._trigger_blink(2)
        elif n == "happy_bounce":
            self.bounce_until = self.now + 650
        elif n == "curious_tilt":
            self.tilt_until = self.now + 950
        elif n == "sleep":
            self.asleep = True
        elif n == "wake":
            self.asleep = False
        elif n == "alert":
            self.alert_until = self.now + 1300
        else:
            return False
        return True

    def _glance(self, x, y, ms):
        self.glance_x = x
        self.glance_y = y
        self.glance_until = self.now + ms

    def _trigger_blink(self, count):
        self.blink_again += count - 1
        self.blink_state = 1
        self.blink_t0 = self.now
        self.blink_duration = 120

    # ---------- update ----------
    def update(self, now):
        self.now = now
        self._update_blink()
        self._update_wander()
        self._update_behaviors()
        self.render()

    def _update_blink(self):
        if not self.p["blink"]:
            self.blink_mult += (1.0 - self.blink_mult) * 0.4
            return
        if self.blink_state == 0:
            if _diff(self.now, self.next_blink) >= 0:
                self.blink_state = 1
                self.blink_t0 = self.now
                self.blink_duration = 100 + self._rand(0, 50)
        elif self.blink_state == 1:
            t = _diff(self.now, self.blink_t0)
            half = self.blink_duration // 2
            if t < half:
                self.blink_mult = 1.0 - (t / half)
            elif t < self.blink_duration:
                self.blink_mult = (t - half) / (self.blink_duration - half)
            else:
                self.blink_mult = 1.0
                self.blink_state = 0
                if self.blink_again > 0:
                    self.blink_again -= 1
                    self.next_blink = self.now + 90
                elif self._rand(0, 100) < 12:
                    # occasional natural double blink
                    self.blink_again = 1
                    self.next_blink = self.now + 130
                else:
                    self.next_blink = self.now + 1800 + self._rand(0, 3600)

    def _update_wander(self):
        if not self.p["idle"] or self.asleep:
            self.wander_x *= 0.9
            self.wander_y *= 0.9
            self.glance_x *= 0.9
            self.glance_y *= 0.9
            return
        if _diff(self.now, self.wander_t) >= 0:
            if self._rand(0, 100) < 18:
                # occasional larger glance
                self.wander_tx = self._rand(-95, 95) / 100.0
                self.wander_ty = self._rand(-60, 60) / 100.0
                self.wander_t = self.now + self._rand(500, 900)
            else:
                self.wander_tx = self._rand(-55, 55) / 100.0
                self.wander_ty = self._rand(-35, 35) / 100.0
                self.wander_t = self.now + self._rand(1400, 3200)
        self.wander_x += (self.wander_tx - self.wander_x) * 0.06
        self.wander_y += (self.wander_ty - self.wander_y) * 0.06
        # micro-saccades: tiny rapid pupil jitter so the gaze never sits still
        if _diff(self.now, self.saccade_t) >= 0:
            self.saccade_tx = self._rand(-20, 20) / 100.0
            self.saccade_ty = self._rand(-15, 15) / 100.0
            self.saccade_t = self.now + self._rand(180, 520)
        self.saccade_x += (self.saccade_tx - self.saccade_x) * 0.35
        self.saccade_y += (self.saccade_ty - self.saccade_y) * 0.35

    def _update_behaviors(self):
        if _diff(self.now, self.glance_until) >= 0:
            self.glance_x *= 0.85
            self.glance_y *= 0.85
        if _diff(self.now, self.bounce_until) >= 0:
            self.bounce_y *= 0.8
        else:
            ph = _diff(self.now, self.bounce_until) * 0.02
            self.bounce_y = math.sin(ph) * 4.0
        if _diff(self.now, self.tilt_until) >= 0:
            self.tilt_x *= 0.85
        else:
            self.tilt_x = 12.0

    # ---------- rendering ----------
    def render(self):
        g = self.g
        g.fillRect(0, 0, self.w, self.h, BG)
        self._draw_accent(g)
        self._draw_brow(g, 0)
        self._draw_brow(g, 1)
        self._draw_eye(g, 0)
        self._draw_eye(g, 1)
        self._draw_mouth(g)
        self._draw_status(g)
        if self.use_canvas:
            g.push(0, 0)

    def _draw_eye(self, g, side):
        p = self.p
        cx, cy, rx = self.eyes[side]
        cx = int(cx + self.tilt_x)
        cy = int(cy + self.bounce_y)

        if side == 0:
            o = p["open_l"]
        else:
            o = p["open_r"]
        o = o * self.blink_mult
        if self.asleep:
            o = min(o, 0.14)
        o = max(0.0, min(1.25, o))

        if p["idle"]:
            # subtle breathing: tiny openness + vertical drift so the face
            # never looks frozen between blinks
            o = o * (1.0 + 0.02 * math.sin(self.now * 0.0016))
            cy = cy + int(1.2 * math.sin(self.now * 0.0022))

        if p["happy"]:
            g.fillArc(cx, cy, rx - 7, rx, 180, 360, LID_LINE)
            return

        if o < 0.06:
            g.fillRoundRect(cx - rx, cy - 2, rx * 2, 4, 2, OUTLINE)
            return

        # sclera (full circle) + iris/pupil, then lids clip it
        g.fillEllipse(cx, cy, rx, rx, SCLERA)
        g.drawEllipse(cx, cy, rx, rx, OUTLINE)

        ox, oy, iris_s = self._effective(side)
        ri = max(3, int(rx * 0.42 * iris_s))
        travel_x = (rx - ri) * 0.78
        travel_y = max((rx * o) - ri, 0) * 0.78
        ix = int(cx + ox * travel_x)
        iy = int(cy + oy * travel_y)
        g.fillCircle(ix, iy, ri, IRIS)
        g.drawCircle(ix, iy, ri, OUTLINE)
        g.fillCircle(ix, iy, max(2, int(ri * 0.55)), PUPIL)
        g.fillCircle(ix - int(ri * 0.30), iy - int(ri * 0.30),
                     max(1, int(ri * 0.16)), 0xFFFFFF)

        cover = int(rx * (1.0 - o))
        if cover > 0:
            g.fillRect(cx - rx - 2, cy - rx, rx * 2 + 4, cover + 1, LID)
            g.fillRect(cx - rx - 2, cy + rx - cover, rx * 2 + 4, cover + 1, LID)
            g.fillRect(cx - rx - 2, cy - rx + cover, rx * 2 + 4, 2, OUTLINE)
            g.fillRect(cx - rx - 2, cy + rx - cover - 2, rx * 2 + 4, 2, OUTLINE)

    def _effective(self, side):
        p = self.p
        if side == 0:
            ox = p["plx"]
            oy = p["ply"]
            iris = p["iris_l"]
        else:
            ox = p["prx"]
            oy = p["pry"]
            iris = p["iris_r"]
        if p["idle"]:
            ox += self.wander_x + self.saccade_x
            oy += self.wander_y + self.saccade_y
        ox += self.glance_x
        oy += self.glance_y
        if p["cross"]:
            ox += 0.55 if side == 0 else -0.55
        if p["think"]:
            t = self.now * 0.003
            ox += math.cos(t) * 0.25
            oy += math.sin(t) * 0.16
        return max(-1.0, min(1.0, ox)), max(-1.0, min(1.0, oy)), iris

    def _draw_brow(self, g, side):
        p = self.p
        cx, cy, rx = self.eyes[side]
        if side == 0:
            lift = p["brow_l_lift"]
            tilt = p["brow_l_tilt"]
        else:
            lift = p["brow_r_lift"]
            tilt = p["brow_r_tilt"]
        yb = int(cy - rx - 10 + lift)
        half = int(rx * 0.92)
        off = int(rx * 0.5)
        y0 = int(yb - tilt * off)
        y1 = int(yb + tilt * off)
        self._thick_line(g, cx - half, y0, cx + half, y1, 4, MOUTH)

    def _draw_mouth(self, g):
        p = self.p
        mx = self.w // 2
        my = int(self.h * 0.82)
        if p["speaking"]:
            ph = self.now * 0.025
            hgt = 4 + int((4 + p["mouth_w"] * 14) * (0.5 + 0.5 * math.sin(ph)))
            g.fillEllipse(mx, my, 11, max(2, hgt), MOUTH)
            return
        m = p["mouth"]
        if m == 0:
            return
        elif m == 1:
            g.fillRoundRect(mx - 16, my - 2, 32, 4, 2, MOUTH)
        elif m == 2:
            g.fillArc(mx, my - 8, 9, 11, 20, 160, MOUTH)
        elif m == 3:
            g.fillArc(mx, my + 8, 9, 11, 200, 340, MOUTH)
        elif m == 4:
            r = 6 + int(p["mouth_w"] * 8)
            g.fillEllipse(mx, my, r, r, MOUTH)
        elif m == 5:
            g.fillRoundRect(mx - 12, my - 1, 24, 3, 2, MOUTH)

    def _draw_accent(self, g):
        p = self.p
        a = p["accent"]
        if _diff(self.now, self.alert_until) < 0:
            a = 2
        if a == 0:
            return
        w = self.w
        h = self.h
        if a == 1:  # listening: pulsing dot bottom-center
            r = 4 + int((self.now % 600) / 600.0 * 5)
            g.drawCircle(w // 2, h - 18, r, ACC_LISTEN)
            g.fillCircle(w // 2, h - 18, 3, ACC_LISTEN)
        elif a == 2:  # alert: blinking exclamation top-right
            if (self.now // 300) % 2 == 0:
                g.fillRoundRect(w - 30, 14, 7, 24, 3, ACC_ALERT)
                g.fillCircle(w - 27, 48, 4, ACC_ALERT)
        elif a == 3:  # error: steady exclamation + top border
            g.fillRoundRect(w - 30, 14, 7, 24, 3, ACC_ERROR)
            g.fillCircle(w - 27, 48, 4, ACC_ERROR)
            g.fillRect(0, 0, w, 3, ACC_ERROR)
        elif a == 4:  # thinking: three pulsing dots
            base = w // 2
            for i in range(3):
                on = ((self.now // 180) % 3) == i
                g.fillCircle(base - 14 + i * 14, h - 20, 4 if on else 2, ACC_THINK)

    def _draw_status(self, g):
        # bottom-left: current state label + MQTT connection dot.
        # Cosmetic only; never let it break the face if a font is missing.
        if not self.status_text:
            return
        try:
            g.setTextColor(self.status_color, BG)
            g.drawString(self.status_text, 8, 200)
            if self.mqtt_state == "connected":
                dot = ACC_LISTEN
            elif self.mqtt_state == "connecting":
                dot = 0xFFD86B
            else:
                dot = ACC_ERROR
            g.fillCircle(12, 224, 4, dot)
            g.setTextColor(0x9AA4B2, BG)
            g.drawString("MQTT", 20, 216)
        except Exception:
            pass

    def _thick_line(self, g, x0, y0, x1, y1, width, color):
        dx = x1 - x0
        dy = y1 - y0
        length = math.sqrt(dx * dx + dy * dy)
        if length < 0.5:
            g.fillCircle(int(x0), int(y0), width // 2, color)
            return
        px = -dy / length * (width / 2.0)
        py = dx / length * (width / 2.0)
        ax = int(x0 + px)
        ay = int(y0 + py)
        bx = int(x0 - px)
        by = int(y0 - py)
        cx2 = int(x1 - px)
        cy2 = int(y1 - py)
        dx2 = int(x1 + px)
        dy2 = int(y1 + py)
        g.fillTriangle(ax, ay, bx, by, cx2, cy2, color)
        g.fillTriangle(ax, ay, dx2, dy2, cx2, cy2, color)

    # ---------- tiny deterministic random ----------
    def _rand(self, lo, hi):
        self._seed ^= (self._seed << 7) & 0xFFFFFFFF
        self._seed ^= self._seed >> 9
        self._seed ^= (self._seed << 8) & 0xFFFFFFFF
        r = self._seed & 0x7FFFFFFF
        return lo + (r % (hi - lo + 1))

# ==== ui/expression_engine.py ====
# SATURDAY HomeBot - expression catalog and emotion mapping.
# Each expression is a full set of EyeEngine parameters (see eye_engine.py).



def _expr(**kw):
    d = dict(DEFAULT_PARAMS)
    d.update(kw)
    return d


EXPRESSIONS = {
    "IDLE": _expr(),
    "BOOTING": _expr(open_l=0.02, open_r=0.02, blink=0, idle=0, mouth=5, accent=0),
    "BLINK": _expr(open_l=0.02, open_r=0.02, blink=0, idle=0, mouth=5),
    "LISTENING": _expr(
        open_l=1.05, open_r=1.05, ply=-0.15, pry=-0.15,
        brow_l_lift=2, brow_r_lift=2, idle=0, blink=1, mouth=1, accent=1),
    "THINKING": _expr(
        open_l=0.82, open_r=0.82, ply=-0.3, pry=-0.3,
        iris_l=0.95, iris_r=0.95,
        brow_l_lift=1, brow_r_lift=1, idle=0, blink=1, think=1, mouth=5),
    "SPEAKING": _expr(
        open_l=1.0, open_r=1.0, speaking=1, mouth_w=0.6, idle=0, blink=1, mouth=0),
    "HAPPY": _expr(
        happy=1, open_l=0.0, open_r=0.0, blink=0, idle=0, mouth=2,
        brow_l_lift=3, brow_r_lift=3),
    "EXCITED": _expr(
        open_l=1.22, open_r=1.22, iris_l=1.18, iris_r=1.18,
        brow_l_lift=4, brow_r_lift=4, blink=1, idle=0, mouth=2),
    "CURIOUS": _expr(
        open_l=0.95, open_r=0.95, prx=0.55, pry=0.1,
        brow_r_lift=4, brow_r_tilt=0.3, blink=1, idle=0, mouth=1),
    "CONFUSED": _expr(
        open_l=0.72, open_r=0.95, plx=-0.55, ply=-0.3, prx=0.55, pry=-0.3,
        brow_l_lift=3, brow_r_lift=0, blink=1, idle=0, mouth=5),
    "SURPRISED": _expr(
        open_l=1.3, open_r=1.3, iris_l=0.72, iris_r=0.72,
        brow_l_lift=6, brow_r_lift=6, blink=0, idle=0, mouth=4, mouth_w=0.7),
    "SLEEPY": _expr(
        open_l=0.35, open_r=0.35, ply=0.5, pry=0.5,
        brow_l_lift=0, brow_r_lift=0, blink=1, idle=0, mouth=5),
    "SAD": _expr(
        open_l=0.8, open_r=0.8, ply=0.45, pry=0.45,
        brow_l_tilt=-0.6, brow_r_tilt=0.6, brow_l_lift=1, brow_r_lift=1,
        blink=1, idle=0, mouth=3),
    "ALERT": _expr(
        open_l=1.1, open_r=1.1, brow_l_lift=2, brow_r_lift=2,
        blink=1, idle=0, mouth=5, accent=2),
    "ERROR": _expr(
        open_l=1.05, open_r=1.05, brow_l_lift=1, brow_r_lift=1,
        brow_l_tilt=-0.2, brow_r_tilt=-0.2, blink=1, idle=0, mouth=5, accent=3),
    "EMERGENCY": _expr(
        open_l=1.2, open_r=1.2, brow_l_lift=3, brow_r_lift=3,
        blink=0, idle=0, mouth=5, accent=3),
}

EMOTION_MAP = {
    "happy": "HAPPY",
    "excited": "EXCITED",
    "curious": "CURIOUS",
    "confused": "CONFUSED",
    "surprised": "SURPRISED",
    "sleepy": "SLEEPY",
    "sad": "SAD",
    "alert": "ALERT",
    "neutral": "IDLE",
    "idle": "IDLE",
    "error": "ERROR",
    "blink": "BLINK",
}


class ExpressionEngine:
    def __init__(self):
        self.exprs = dict(EXPRESSIONS)
        self.emap = dict(EMOTION_MAP)

    def has_expression(self, name):
        return str(name).upper() in self.exprs

    def expression_name(self, name):
        n = str(name).upper()
        return n if n in self.exprs else "IDLE"

    def params(self, name):
        n = self.expression_name(name)
        return self.exprs[n]

    def emotion_to_expression(self, emotion):
        e = str(emotion).lower().strip()
        return self.emap.get(e, None)

# ==== ui/animation_controller.py ====
# SATURDAY HomeBot - expression interpolation + priority resolution.
# AnimationController smooths transitions between expression parameter sets.
# EmotionController resolves operational vs cosmetic expression sources.

import time



def _now():
    try:
        return time.ticks_ms()
    except Exception:
        return int(time.time() * 1000)


# Expressions that must snap instantly instead of cross-fading.
INSTANT = {"BLINK", "BOOTING"}


class AnimationController:
    def __init__(self, engine=None, tau_ms=110):
        self.engine = engine if engine is not None else ExpressionEngine()
        self.tau = tau_ms
        self.current = dict(DEFAULT_PARAMS)
        self.target = dict(DEFAULT_PARAMS)
        self.current_name = "IDLE"
        self.last = None

    def set_expression(self, name):
        n = self.engine.expression_name(name)
        if n == self.current_name:
            return
        self.current_name = n
        self.target = self.engine.params(n)
        if n in INSTANT:
            for k in NUM_KEYS:
                self.current[k] = self.target[k]
            for k in CAT_KEYS:
                self.current[k] = self.target[k]

    def update(self, now):
        dt = 16
        if self.last is not None:
            try:
                dt = time.ticks_diff(now, self.last)
            except Exception:
                dt = now - self.last
        self.last = now
        if dt <= 0:
            dt = 1
        k = dt / self.tau
        if k > 1.0:
            k = 1.0
        for key in NUM_KEYS:
            self.current[key] += (self.target[key] - self.current[key]) * k
        for key in CAT_KEYS:
            self.current[key] = self.target[key]


class EmotionController:
    """Resolves the active expression from operational + emotion sources.

    Priority (highest first):
      EMERGENCY > ERROR > LISTENING > THINKING > SPEAKING > emotion > IDLE
    """

    def __init__(self, engine=None):
        self.engine = engine if engine is not None else ExpressionEngine()
        self.emergency = False
        self.error = False
        self.listening = False
        self.thinking = False
        self.speaking = False
        self.emotion = None
        self.emotion_until = 0
        self.last_name = "IDLE"
        self.now = 0

    def set_operational(self, key, value):
        if key == "emergency":
            self.emergency = value
        elif key == "error":
            self.error = value
        elif key == "listening":
            self.listening = value
        elif key == "thinking":
            self.thinking = value
        elif key == "speaking":
            self.speaking = value

    def set_emotion(self, emotion_or_expr, duration_ms=3000):
        u = str(emotion_or_expr).upper()
        if self.engine.has_expression(u):
            expr = u
        else:
            expr = self.engine.emotion_to_expression(emotion_or_expr)
        if expr is None or expr == "IDLE":
            self.emotion = None
            self.emotion_until = 0
            return
        self.emotion = expr
        self.emotion_until = self.now + duration_ms

    def resolve(self):
        if self.emergency:
            return "EMERGENCY"
        if self.error:
            return "ERROR"
        if self.listening:
            return "LISTENING"
        if self.thinking:
            return "THINKING"
        if self.speaking:
            # keep the emotion face while speaking; fall back to SPEAKING face
            if (self.emotion is not None and self.now < self.emotion_until
                    and self.emotion not in ("ERROR", "ALERT", "EMERGENCY")):
                return self.emotion
            return "SPEAKING"
        if self.emotion is not None and self.now < self.emotion_until:
            return self.emotion
        self.emotion = None
        return "IDLE"

    def update(self, now):
        self.now = now
        self.last_name = self.resolve()
        return self.last_name

# ==== voice/audio_capture.py ====
# SATURDAY HomeBot - bounded microphone capture with energy-based VAD.
# Core2 has no reliable local STT; this only captures bounded PCM segments
# and detects speech onset/offset. Transcription happens on SATURDAY.

try:
    from M5 import *
except ImportError:
    pass


class AudioCapture:
    IDLE = 0
    WAIT = 1
    DONE = 2

    def __init__(self, sample_rate=8000, window_ms=160, max_ms=6000):
        self.sr = sample_rate
        self.window_ms = window_ms
        self.window_bytes = int(sample_rate * window_ms / 1000)
        self.window = bytearray(self.window_bytes)
        self.max_bytes = int(sample_rate * max_ms / 1000)
        self.acc = bytearray(self.max_bytes)
        self.acc_len = 0
        self.state = self.IDLE
        self.mode = "capture"
        self.threshold = 120
        self.silence_ms = 700
        self.had_speech = False
        self.silence_acc = 0
        self.elapsed = 0
        self.last_energy = 0
        self.started = False
        self.arm_request = None

    def begin(self):
        if not self.started:
            Mic.begin()
            Mic.setSampleRate(self.sr)
            self.started = True

    def end(self):
        if self.started:
            Mic.end()
            self.started = False

    def _switch_to_capture(self, threshold, silence_ms):
        self.mode = "capture"
        self.threshold = threshold
        self.silence_ms = silence_ms
        self.acc_len = 0
        self.had_speech = False
        self.silence_acc = 0
        self.elapsed = 0
        self.state = self.WAIT

    def _switch_to_sniff(self, threshold):
        self.mode = "sniff"
        self.threshold = threshold
        self.had_speech = False
        self.state = self.WAIT

    def start(self, threshold=120, silence_ms=700):
        self.begin()
        self.arm_request = None
        self._switch_to_capture(threshold, silence_ms)
        Mic.record(self.window, self.sr, False)

    def sniff_start(self, threshold=140):
        self.begin()
        self.arm_request = None
        self._switch_to_sniff(threshold)
        Mic.record(self.window, self.sr, False)

    def arm_capture(self, threshold, silence_ms):
        # Switch from passive sniffing to a real capture at the next safe
        # window boundary (or immediately if the sniff already finished).
        if self.state == self.DONE:
            self.begin()
            self._switch_to_capture(threshold, silence_ms)
            Mic.record(self.window, self.sr, False)
        else:
            self.arm_request = (threshold, silence_ms)

    def update(self):
        # returns None while busy, "sniff" when speech onset detected,
        # "done" when a bounded capture finished.
        if self.state == self.IDLE or self.state == self.DONE:
            return None
        if Mic.isRecording() != 0:
            return None

        # window just finished
        if self.arm_request is not None:
            thr, sil = self.arm_request
            self.arm_request = None
            self._switch_to_capture(thr, sil)
            Mic.record(self.window, self.sr, False)
            return None

        energy = self._energy(self.window, self.window_bytes)
        self.last_energy = energy

        if self.mode == "sniff":
            if energy >= self.threshold:
                self.state = self.DONE
                return "sniff"
            Mic.record(self.window, self.sr, False)
            return None

        # capture mode
        self.elapsed += self.window_ms
        if energy >= self.threshold:
            self.had_speech = True
            self.silence_acc = 0
        if self.had_speech:
            if energy < self.threshold:
                self.silence_acc += self.window_ms
            n = min(self.window_bytes, self.max_bytes - self.acc_len)
            self.acc[self.acc_len:self.acc_len + n] = self.window[:n]
            self.acc_len += n

        if self.acc_len >= self.max_bytes:
            self.state = self.DONE
            return "done"
        if self.had_speech and self.silence_acc >= self.silence_ms:
            self.state = self.DONE
            return "done"
        if not self.had_speech and self.elapsed >= 5000:
            self.state = self.DONE
            return "done"

        Mic.record(self.window, self.sr, False)
        return None

    def get_audio(self):
        return bytes(self.acc[:self.acc_len])

    def audio_len(self):
        return self.acc_len

    def has_speech(self):
        return self.had_speech

    def _energy(self, buf, n):
        total = 0
        i = 0
        while i < n - 1:
            v = buf[i] | (buf[i + 1] << 8)
            if v >= 0x8000:
                v -= 0x10000
            if v < 0:
                v = -v
            total += v
            i += 2
        if i >= 2:
            return total // (i // 2)
        return 0

# ==== voice/speech_output.py ====
# SATURDAY HomeBot - speech playback abstraction.
# Core2 has no reliable local TTS, so TEXT_RESPONSE falls back to a friendly
# chime while AUDIO_RESPONSE (PCM/WAV from SATURDAY) is played via Speaker.
# Replace or subclass this to add a future TTS streaming implementation.

try:
    from M5 import *
except ImportError:
    pass


class SpeechOutput:
    def __init__(self, volume_pct=65):
        self.volume_pct = volume_pct
        self.started = False
        self.fallback_text = "I'm having trouble reaching SATURDAY."

    def begin(self):
        if self.started:
            return
        Speaker.begin()
        Speaker.setVolumePercentage(self.volume_pct)
        self.started = True

    def end(self):
        if self.started:
            try:
                Speaker.end()
            except Exception:
                pass
            self.started = False

    def ensure(self):
        if not self.started:
            self.begin()

    def is_playing(self):
        try:
            return Speaker.isPlaying()
        except Exception:
            return False

    def update(self, now):
        pass

    def speak_text(self, text):
        # No local TTS engine on Core2: acknowledge with a soft chime.
        self.ensure()
        self._chime()
        return False

    def play_pcm(self, data, rate):
        self.ensure()
        Speaker.playRaw(data, rate, False)
        return True

    def play_wav(self, data):
        self.ensure()
        Speaker.playWav(data)
        return True

    def stop(self):
        try:
            Speaker.stop()
        except Exception:
            pass

    def _chime(self):
        try:
            Speaker.tone(784, 90)
            Speaker.tone(1046, 110)
        except Exception:
            pass

# ==== voice/voice_transport.py ====
# SATURDAY HomeBot - voice transport abstraction.
# Splits bounded PCM into base64 chunks with correlation IDs so broker
# message-size limits are never hit. Mode A (local transcript) is not used by
# default because Core2 has no reliable local STT; Mode B (audio forwarding)
# is preferred.

import time
import ubinascii


def _now():
    try:
        return time.ticks_ms()
    except Exception:
        return int(time.time() * 1000)


class VoiceTransport:
    def __init__(self, protocol, device_id, sample_rate=8000,
                 audio_format="pcm_s16le", chunk_size=2048, mode="audio"):
        self.protocol = protocol
        self.device_id = device_id
        self.sample_rate = sample_rate
        self.audio_format = audio_format
        self.chunk_size = chunk_size
        self.mode = mode  # "audio" (AUDIO_FORWARDING) or "transcript" (LOCAL_TRANSCRIPT)
        self.corr_counter = 0
        self.current_corr = None

    def new_correlation(self):
        self.corr_counter += 1
        self.current_corr = "hb_%d_%d" % (_now() & 0xFFFFFF, self.corr_counter)
        return self.current_corr

    def request_meta(self, corr, text=None):
        return {
            "type": "voice_request",
            "device_id": self.device_id,
            "session_id": "s_%d" % (_now() & 0xFFFF),
            "correlation_id": corr,
            "timestamp": _now(),
            "audio_format": self.audio_format,
            "sample_rate": self.sample_rate,
            "mode": self.mode,
            "text": text if text is not None else "",
        }

    def split_chunks(self, audio_bytes):
        n = len(audio_bytes)
        if n == 0:
            return [""], 1
        total = (n + self.chunk_size - 1) // self.chunk_size
        chunks = []
        for i in range(total):
            seg = audio_bytes[i * self.chunk_size:(i + 1) * self.chunk_size]
            chunks.append(ubinascii.b2a_base64(seg).decode().strip())
        return chunks, total

    def chunk_msg(self, corr, idx, total, payload):
        return {
            "type": "voice_chunk",
            "correlation_id": corr,
            "chunk_index": idx,
            "total_chunks": total,
            "payload": payload,
        }

    def end_msg(self, corr):
        return {
            "type": "voice_end",
            "correlation_id": corr,
            "device_id": self.device_id,
        }

# ==== communication/mqtt_voice_protocol.py ====
# SATURDAY HomeBot - MQTT voice protocol with broker failover.
# Primary broker is preferred; secondary is failover. Reconnects always try the
# primary first so the link recovers back to the preferred broker gracefully.

import time

try:
    import ujson
except ImportError:
    import json as ujson

try:
    from umqtt import MQTTClient
except ImportError:
    MQTTClient = None


def _now():
    try:
        return time.ticks_ms()
    except Exception:
        return int(time.time() * 1000)


def _diff(a, b):
    try:
        return time.ticks_diff(a, b)
    except Exception:
        return a - b


class MqttVoiceProtocol:
    def __init__(self, device_id, brokers, prefix="saturday/homebot"):
        self.device_id = device_id
        self.brokers = brokers  # list of (host, port)
        self.prefix = prefix
        self.client_id = "%s_%d" % (device_id, _now() % 100000)
        self.client = None
        self.active = 0
        self.connected = False
        self.last_error = None
        self.next_reconnect = 0
        self.heartbeat_interval = 30000
        self.last_heartbeat = 0
        self.on_response = None
        self.on_behavior = None
        self.on_audio_chunk = None

        self.topic_request = "%s/%s/voice/request" % (prefix, device_id)
        self.topic_chunk = "%s/%s/voice/chunk" % (prefix, device_id)
        self.topic_end = "%s/%s/voice/end" % (prefix, device_id)
        self.topic_status = "%s/%s/status" % (prefix, device_id)
        self.topic_response = "%s/%s/response" % (prefix, device_id)
        self.topic_audio = "%s/%s/audio" % (prefix, device_id)
        self.topic_behavior = "%s/%s/behavior" % (prefix, device_id)

    # ---------- connection management ----------
    def connect(self):
        if MQTTClient is None:
            return False
        self._teardown()
        # always try the primary (index 0) first so we prefer it on reconnect
        for i in range(len(self.brokers)):
            host, port = self.brokers[i]
            try:
                c = MQTTClient(self.client_id, host, port=port,
                               user=None, password=None, keepalive=30)
                c.connect(clean_session=True)
                self.client = c
                self.connected = True
                try:
                    self._subscribe_all()
                except Exception as e:
                    self.last_error = e
                    self._teardown()
                    continue
                self.active = i
                return True
            except Exception as e:
                self.last_error = e
                self.connected = False
                self.client = None
                continue
        self.client = None
        self.connected = False
        return False

    def _teardown(self):
        if self.client is not None:
            try:
                self.client.disconnect()
            except Exception:
                pass
            self.client = None
        self.connected = False

    def is_connected(self):
        return self.connected and self.client is not None

    def _subscribe_all(self):
        self.client.subscribe(self.topic_response, self._on_message, qos=0)
        self.client.subscribe(self.topic_audio, self._on_message, qos=0)
        self.client.subscribe(self.topic_behavior, self._on_message, qos=0)

    # ---------- periodic service ----------
    def poll(self, now):
        if not self.is_connected():
            if _diff(now, self.next_reconnect) >= 0:
                self.next_reconnect = now + 5000
                self.connect()
            return
        try:
            self.client.check_msg()
        except Exception as e:
            self.last_error = e
            self.connected = False
            self.client = None
            self.next_reconnect = now + 2000
            return
        if _diff(now, self.last_heartbeat) >= self.heartbeat_interval:
            self.publish_status({
                "type": "status",
                "device_id": self.device_id,
                "state": "alive",
                "timestamp": now,
            })
            self.last_heartbeat = now

    # ---------- publishing ----------
    def publish(self, topic, obj):
        if not self.is_connected():
            return False
        try:
            self.client.publish(topic, ujson.dumps(obj), qos=0)
            return True
        except Exception as e:
            self.last_error = e
            self.connected = False
            self.client = None
            self.next_reconnect = _now() + 2000
            return False

    def publish_status(self, obj):
        return self.publish(self.topic_status, obj)

    # ---------- message dispatch ----------
    def _on_message(self, data):
        try:
            topic = data[0]
            payload = data[1]
        except Exception:
            return
        self._dispatch(topic, payload)

    def _dispatch(self, topic, payload):
        try:
            if isinstance(payload, (bytes, bytearray)):
                payload = payload.decode()
            obj = ujson.loads(payload)
        except Exception:
            return
        t = obj.get("type")
        if t == "ai_response" and self.on_response is not None:
            self.on_response(obj)
        elif t == "audio_chunk" and self.on_audio_chunk is not None:
            self.on_audio_chunk(obj)
        elif t == "behavior" and self.on_behavior is not None:
            self.on_behavior(obj)

# ==== voice/voice_interaction.py ====
# SATURDAY HomeBot - voice interaction state machine.
# Flow: IDLE -> LISTENING -> THINKING -> WAITING_FOR_SATURDAY -> SPEAKING -> IDLE
# with response timeout, retry, and local fallback. Never blocks motor safety.

import time
import ubinascii


def _now():
    try:
        return time.ticks_ms()
    except Exception:
        return int(time.time() * 1000)


def _diff(a, b):
    try:
        return time.ticks_diff(a, b)
    except Exception:
        return a - b


class VoiceInteractionManager:
    ST_IDLE = "IDLE"
    ST_LISTENING = "LISTENING"
    ST_THINKING = "THINKING"
    ST_WAITING = "WAITING"
    ST_SPEAKING = "SPEAKING"

    def __init__(self, audio, transport, speech, protocol, config=None):
        self.audio = audio
        self.transport = transport
        self.speech = speech
        self.protocol = protocol
        c = config or {}
        self.response_timeout = c.get("response_timeout_ms", 8000)
        self.max_retries = c.get("max_retries", 1)
        self.vad_trigger = c.get("vad_trigger", True)
        self.vad_threshold = c.get("vad_threshold", 140)
        self.speech_threshold = c.get("speech_threshold", 120)
        self.silence_ms = c.get("silence_ms", 700)

        self.state = self.ST_IDLE
        self.on_state = None
        self.on_emotion = None
        self.on_text = None

        self.current_corr = None
        self.pending_chunks = []
        self.pending_total = 0
        self.pending_idx = 0
        self.wait_started = 0
        self.retries = 0
        self.response_received = False
        self.sniffing = False

        self.playback_started = False
        self.expect_audio = False
        self.audio_wait_started = 0
        self.audio_pending = None
        self.audio_parts = None
        self.audio_total = 0
        self.audio_count = 0

    # ---------- public triggers ----------
    def start_listening(self):
        if self.state in (self.ST_SPEAKING, self.ST_LISTENING):
            return
        self.speech.end()
        self.sniffing = False
        if self.audio.state == self.audio.WAIT and self.audio.mode == "sniff":
            self.audio.arm_capture(self.speech_threshold, self.silence_ms)
        else:
            self.audio.start(self.speech_threshold, self.silence_ms)
        self._goto(self.ST_LISTENING)

    def interrupt(self):
        self.speech.stop()
        self.audio.end()
        self.sniffing = False
        self.current_corr = None
        self.pending_chunks = []
        self.pending_total = 0
        self.pending_idx = 0
        self.response_received = False
        self.playback_started = False
        self.expect_audio = False
        self.audio_pending = None
        self.audio_parts = None
        self._goto(self.ST_IDLE)

    def _goto(self, st):
        if self.state == st:
            return
        self.state = st
        if self.on_state is not None:
            self.on_state(st)

    # ---------- periodic update ----------
    def update(self, now):
        st = self.state

        if st == self.ST_IDLE:
            if self.vad_trigger:
                if not self.sniffing:
                    self.audio.sniff_start(self.vad_threshold)
                    self.sniffing = True
                res = self.audio.update()
                if res == "sniff":
                    self.sniffing = False
                    self.start_listening()
            return

        if st == self.ST_LISTENING:
            res = self.audio.update()
            if res == "done":
                self._on_capture_done()
            return

        if st == self.ST_THINKING:
            sent = 0
            while self.pending_idx < self.pending_total and sent < 4:
                chunk = self.pending_chunks[self.pending_idx]
                self.protocol.publish(
                    self.protocol.topic_chunk,
                    self.transport.chunk_msg(self.current_corr,
                                             self.pending_idx,
                                             self.pending_total,
                                             chunk))
                self.pending_idx += 1
                sent += 1
            if self.pending_idx >= self.pending_total:
                self.protocol.publish(
                    self.protocol.topic_end,
                    self.transport.end_msg(self.current_corr))
                self._goto(self.ST_WAITING)
                self.wait_started = now
                self.response_received = False
            return

        if st == self.ST_WAITING:
            if _diff(now, self.wait_started) >= self.response_timeout:
                if self.retries < self.max_retries:
                    self.retries += 1
                    self._resend_request()
                else:
                    self._fallback_timeout()
            return

        if st == self.ST_SPEAKING:
            if self.playback_started and not self.speech.is_playing():
                self._finish_speaking()
                return
            if self.expect_audio and _diff(now, self.audio_wait_started) >= self.response_timeout:
                self._fallback_timeout()
            return

    # ---------- capture completion ----------
    def _on_capture_done(self):
        data = self.audio.get_audio()
        self.audio.end()
        self.sniffing = False
        if not data or not self.audio.has_speech():
            self._goto(self.ST_IDLE)
            return

        self.current_corr = self.transport.new_correlation()
        self.retries = 0
        self.response_received = False
        self.playback_started = False
        self.expect_audio = False
        self.audio_pending = None
        self.audio_parts = None
        self.audio_count = 0
        self.audio_total = 0

        meta = self.transport.request_meta(self.current_corr)
        if self.transport.mode == "audio":
            self.pending_chunks, self.pending_total = self.transport.split_chunks(data)
        else:
            # LOCAL_TRANSCRIPT: Core2 has no reliable STT, send an empty
            # transcript marker for SATURDAY-side handling.
            meta["text"] = ""
            self.pending_chunks = []
            self.pending_total = 0
        self.pending_idx = 0
        self.protocol.publish(self.protocol.topic_request, meta)
        self._goto(self.ST_THINKING)

    def _resend_request(self):
        self.pending_idx = 0
        self.response_received = False
        meta = self.transport.request_meta(self.current_corr)
        self.protocol.publish(self.protocol.topic_request, meta)
        self._goto(self.ST_THINKING)

    def _fallback_timeout(self):
        self.current_corr = None
        self.pending_chunks = []
        self.expect_audio = False
        self.audio_pending = None
        self.audio_parts = None
        if self.on_text is not None:
            self.on_text(self.speech.fallback_text)
        if self.on_emotion is not None:
            self.on_emotion("sad", "SAD", None, 3000)
        self._start_text("")

    def _finish_speaking(self):
        self.playback_started = False
        self.expect_audio = False
        self.current_corr = None
        self.pending_chunks = []
        self.audio_pending = None
        self.audio_parts = None
        self.speech.end()
        self._goto(self.ST_IDLE)

    # ---------- inbound SATURDAY messages ----------
    def on_ai_response(self, msg):
        corr = msg.get("correlation_id")
        if self.current_corr is not None and corr != self.current_corr:
            return
        self.response_received = True

        text = msg.get("text") or ""
        emotion = msg.get("emotion")
        expression = msg.get("expression")
        dur = 3000
        if text:
            dur = max(3000, min(12000, len(text) * 90))
        if self.on_emotion is not None:
            self.on_emotion(emotion, expression, msg, dur)
        if self.on_text is not None:
            self.on_text(text)

        mode = msg.get("speech_mode", "text")
        if mode == "audio":
            emb = msg.get("audio")
            if emb:
                try:
                    data = ubinascii.a2b_base64(emb)
                except Exception:
                    data = b""
                self._start_audio(data, msg.get("sample_rate", self.transport.sample_rate))
            elif self.audio_pending is not None:
                self._start_audio(self.audio_pending[0], self.audio_pending[1])
            else:
                self.expect_audio = True
                self.audio_wait_started = _now()
                self._goto(self.ST_SPEAKING)
        else:
            self._start_text(text)

    def on_audio_chunk(self, msg):
        if self.current_corr is not None and msg.get("correlation_id") != self.current_corr:
            return
        idx = msg.get("chunk_index", 0)
        total = msg.get("total_chunks", 1)
        if self.audio_parts is None or self.audio_total != total:
            self.audio_parts = [None] * total
            self.audio_total = total
            self.audio_count = 0
        if 0 <= idx < total and self.audio_parts[idx] is None:
            payload = msg.get("payload") or ""
            try:
                data = ubinascii.a2b_base64(payload)
            except Exception:
                data = b""
            self.audio_parts[idx] = data
            self.audio_count += 1
        if self.audio_count >= self.audio_total:
            buf = bytearray()
            for part in self.audio_parts:
                if part is not None:
                    buf += part
            rate = msg.get("sample_rate", self.transport.sample_rate)
            self.audio_pending = (bytes(buf), rate)
            self.audio_parts = None
            if self.response_received and self.state == self.ST_SPEAKING:
                self._start_audio(self.audio_pending[0], self.audio_pending[1])

    # ---------- playback ----------
    def _start_text(self, text):
        self.playback_started = True
        self.expect_audio = False
        self.speech.speak_text(text)
        self._goto(self.ST_SPEAKING)

    def _start_audio(self, data, rate):
        if not data:
            self._start_text("")
            return
        self.playback_started = True
        self.expect_audio = False
        self.audio_pending = None
        self.speech.play_pcm(data, rate)
        self._goto(self.ST_SPEAKING)

# ==== core/embodiment_controller.py ====
# SATURDAY HomeBot - embodiment coordinator.
# Wires the EyeEngine, expression/emotion controllers, voice interaction,
# speech output and SATURDAY MQTT messages into one non-blocking system.

import time



def _now():
    try:
        return time.ticks_ms()
    except Exception:
        return int(time.time() * 1000)


def _diff(a, b):
    try:
        return time.ticks_diff(a, b)
    except Exception:
        return a - b


class EmbodimentController:
    def __init__(self, cfg, w=320, h=240):
        self.cfg = cfg
        self.eye = EyeEngine(w, h)
        self.expr = ExpressionEngine()
        self.animator = AnimationController(self.expr)
        self.emotion = EmotionController(self.expr)
        self.speech = SpeechOutput(volume_pct=cfg.get("volume_pct", 65))
        self.audio = AudioCapture(sample_rate=cfg.get("sample_rate", 8000))
        self.protocol = MqttVoiceProtocol(cfg["device_id"], cfg["brokers"])
        self.transport = VoiceTransport(
            self.protocol,
            cfg["device_id"],
            sample_rate=cfg.get("sample_rate", 8000),
            audio_format=cfg.get("audio_format", "pcm_s16le"),
            chunk_size=cfg.get("chunk_size", 2048),
            mode=cfg.get("transport_mode", "audio"),
        )
        self.voice = VoiceInteractionManager(
            self.audio, self.transport, self.speech, self.protocol, cfg)

        self.protocol.on_response = self._on_response
        self.protocol.on_behavior = self._on_behavior
        self.protocol.on_audio_chunk = self._on_audio_chunk
        self.voice.on_state = self._on_voice_state
        self.voice.on_emotion = self._on_emotion
        self.voice.on_text = self._on_text

        self.boot_start = 0
        self.boot_ms = 900
        self.last_text = ""

    # ---------- lifecycle ----------
    def begin(self):
        self.eye.begin()
        self.protocol.connect()
        self.boot_start = _now()

    def update(self, now):
        self.protocol.poll(now)
        self.voice.update(now)
        if _diff(now, self.boot_start) < self.boot_ms:
            name = "BOOTING"
            label = "BOOTING"
            scolor = 0x9AA4B2
        else:
            name = self.emotion.update(now)
            label, scolor = self._status_label()

        if self.protocol.is_connected():
            mqtt = "connected"
        elif self.protocol.next_reconnect:
            mqtt = "connecting"
        else:
            mqtt = "disconnected"
        self.eye.set_status(label, mqtt, scolor)

        self.animator.set_expression(name)
        self.animator.update(now)
        self.eye.set_params(self.animator.current)
        self.eye.update(now)

    def _status_label(self):
        if self.emotion.emergency:
            return "EMERGENCY", 0xFF3B30
        if self.emotion.error:
            return "ERROR", 0xFF3B30
        st = self.voice.state
        if st == "LISTENING":
            return "LISTENING", 0x3DF0A8
        if st == "THINKING":
            return "THINKING", 0x7FD0FF
        if st == "WAITING":
            return "WAITING", 0x7FD0FF
        if st == "SPEAKING":
            return "SPEAKING", 0xFFFFFF
        return "IDLE", 0xCBD5E1

    # ---------- external triggers ----------
    def tap(self):
        self.voice.start_listening()

    def set_emergency(self, active, reason=""):
        self.emotion.set_operational("emergency", active)
        if active:
            self.voice.interrupt()
            self.speech.stop()
            self.eye.command("alert")

    def set_error(self, active):
        self.emotion.set_operational("error", active)

    # ---------- voice / protocol callbacks ----------
    def _on_voice_state(self, st):
        self.emotion.set_operational("listening", st == "LISTENING")
        self.emotion.set_operational("thinking", st in ("THINKING", "WAITING"))
        self.emotion.set_operational("speaking", st == "SPEAKING")

    def _on_emotion(self, emotion, expression, msg, duration_ms=3000):
        self.emotion.set_emotion(expression or emotion, duration_ms)

    def _on_text(self, text):
        self.last_text = text
        if text:
            print("[SATURDAY]", text)

    def _on_response(self, msg):
        self.voice.on_ai_response(msg)

    def _on_behavior(self, msg):
        name = msg.get("behavior") or msg.get("action")
        if name:
            self.eye.command(name)

    def _on_audio_chunk(self, msg):
        self.voice.on_audio_chunk(msg)

# ==== main ====
# SATURDAY HomeBot - embodied voice terminal (M5Stack Core2).
# SATURDAY is the main intelligence; HomeBot is its physical face and voice
# interface. All reasoning/STT/TTS happens on SATURDAY over MQTT.

import time
import M5
from M5 import *


CONFIG = {
    "device_id": "saturday_homebot_01",
    "brokers": [("192.168.0.1", 1883), ("192.168.0.180", 1883)],
    "sample_rate": 8000,
    "audio_format": "pcm_s16le",
    "chunk_size": 2048,
    "transport_mode": "audio",   # "audio" (AUDIO_FORWARDING) or "transcript"
    "response_timeout_ms": 8000,
    "max_retries": 1,
    "vad_trigger": True,
    "vad_threshold": 140,
    "speech_threshold": 120,
    "silence_ms": 700,
    "volume_pct": 65,
}


class RobotSystem:
    """Non-blocking safety/robotics integration point.

    Wire the real motor drivers, encoders and bumpers here. Every call must be
    short and non-blocking so facial animation, voice and MQTT never stall.
    """

    def __init__(self):
        self.emergency = False
        self.error = False

    def update(self, now):
        # TODO: poll encoders / motor drivers / bumpers (short, non-blocking).
        pass

    def emergency_stop(self, reason=""):
        self.emergency = True
        print("EMERGENCY_STOP:", reason)

    def clear_emergency(self):
        self.emergency = False

    def set_error(self, active):
        self.error = active


robot = None
embodiment = None
last_touch = 0
prev_emergency = False


def _now():
    try:
        return time.ticks_ms()
    except Exception:
        return int(time.time() * 1000)


def _diff(a, b):
    try:
        return time.ticks_diff(a, b)
    except Exception:
        return a - b


def _screen_size():
    w = 0
    h = 0
    try:
        w = M5.Lcd.width()
        h = M5.Lcd.height()
    except Exception:
        try:
            w = M5.Display.width()
            h = M5.Display.height()
        except Exception:
            return 320, 240
    return w, h


def setup():
    global robot, embodiment, last_touch
    M5.begin()

    # ensure landscape orientation for the two-eye face
    w, h = _screen_size()
    if w < h:
        try:
            M5.Lcd.setRotation(1)
        except Exception:
            try:
                M5.Display.setRotation(1)
            except Exception:
                pass
        w, h = _screen_size()
    if w == 0 or h == 0:
        w, h = 320, 240

    robot = RobotSystem()
    embodiment = EmbodimentController(CONFIG, w=w, h=h)
    embodiment.begin()
    last_touch = 0


def loop():
    global last_touch, prev_emergency
    M5.update()
    now = _now()

    robot.update(now)

    # touch tap -> start listening
    if M5.Touch.getCount():
        if _diff(now, last_touch) > 600:
            last_touch = now
            embodiment.tap()

    # emergency propagation (edge-triggered): mirror the robotics layer
    if robot.emergency and not prev_emergency:
        embodiment.set_emergency(True)
    elif not robot.emergency and prev_emergency:
        embodiment.set_emergency(False)
    prev_emergency = robot.emergency
    embodiment.set_error(robot.error)

    embodiment.update(now)
    time.sleep_ms(16)


if __name__ == "__main__":
    try:
        setup()
        while True:
            loop()
    except (Exception, KeyboardInterrupt) as e:
        try:
            from utility import print_error_msg
            print_error_msg(e)
        except ImportError:
            print("err:", e)
