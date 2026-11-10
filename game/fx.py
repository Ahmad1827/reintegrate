"""Shared look-and-feel helpers: palette, text, glows, film grain, particles, sound."""
import math
import random

import pygame

try:
    import numpy as np
except Exception:  # numpy is needed for grain + sound; the game still runs without
    np = None

W, H = 1280, 720
BAR = 46  # letterbox bar height

INK = (16, 20, 28)
SKIN = (226, 178, 148)
SKIN_D = (188, 138, 114)
SKIN_L = (240, 204, 178)
CUFF = (224, 220, 206)
WARM = (246, 196, 120)


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def lerp(a, b, t):
    return a + (b - a) * t


def mix(c1, c2, t):
    return tuple(int(lerp(c1[i], c2[i], t)) for i in range(3))


# ---------------------------------------------------------------- text
_fonts = {}
_texts = {}


def font(size, italic=False):
    key = (size, italic)
    if key not in _fonts:
        try:
            f = pygame.font.SysFont(
                "georgia,cambria,palatinolinotype,dejavuserif,liberationserif,timesnewroman",
                size, italic=italic)
        except Exception:
            f = pygame.font.Font(None, size)
        _fonts[key] = f
    return _fonts[key]


def text(surf, s, size, color, pos, center=True, alpha=255, italic=False, spacing=0):
    if alpha <= 2 or not s:
        return
    key = (s, size, color, italic, spacing)
    img = _texts.get(key)
    if img is None:
        f = font(size, italic)
        if spacing:
            glyphs = [f.render(ch, True, color) for ch in s]
            w = sum(g.get_width() for g in glyphs) + spacing * (len(s) - 1)
            img = pygame.Surface((w, f.get_height()), pygame.SRCALPHA)
            x = 0
            for g in glyphs:
                img.blit(g, (x, 0))
                x += g.get_width() + spacing
        else:
            img = f.render(s, True, color)
        if len(_texts) > 400:
            _texts.clear()
        _texts[key] = img
    img.set_alpha(int(alpha))
    r = img.get_rect()
    if center:
        r.center = pos
    else:
        r.topleft = pos
    surf.blit(img, r)


# ---------------------------------------------------------------- light
_glows = {}


def add_glow(surf, pos, radius, color, k=1.0):
    """Additive soft light."""
    radius = max(8, int(radius) // 8 * 8)
    col = tuple(int(clamp(c * k, 0, 255)) // 8 * 8 for c in color)
    key = (radius, col)
    g = _glows.get(key)
    if g is None:
        g = pygame.Surface((radius * 2, radius * 2))
        for r in range(radius, 0, -2):
            f = (1 - r / radius) ** 2.2
            pygame.draw.circle(g, tuple(int(c * f) for c in col), (radius, radius), r)
        g = g.convert()
        if len(_glows) > 300:
            _glows.clear()
        _glows[key] = g
    surf.blit(g, (pos[0] - radius, pos[1] - radius), special_flags=pygame.BLEND_RGB_ADD)


def vgrad(w, h, top, bot):
    s = pygame.Surface((w, h))
    for y in range(h):
        pygame.draw.line(s, mix(top, bot, y / (h - 1)), (0, y), (w, y))
    return s


def make_vignette():
    s = pygame.Surface((W, H), pygame.SRCALPHA)
    if np is None:
        return s
    w, h = W // 4, H // 4
    xs = (np.arange(w) - w / 2) / (w / 2)
    ys = (np.arange(h) - h / 2) / (h / 2)
    d = np.sqrt(xs[:, None] ** 2 + (ys[None, :] * 0.9) ** 2)
    a = (np.clip((d - 0.45) / 0.85, 0, 1) ** 1.6 * 215).astype(np.uint8)
    small = pygame.Surface((w, h), pygame.SRCALPHA)
    small.fill((6, 8, 14, 0))
    pygame.surfarray.pixels_alpha(small)[:] = a
    return pygame.transform.smoothscale(small, (W, H))


def make_grain(n=4):
    out = []
    if np is None:
        return out
    rng = np.random.default_rng(3)
    for _ in range(n):
        g = rng.integers(0, 17, (W // 2, H // 2), dtype=np.uint8)
        s = pygame.surfarray.make_surface(np.dstack([g, g, g]))
        out.append(pygame.transform.scale(s, (W, H)).convert())
    return out


# ---------------------------------------------------------------- particles
class Particles:
    def __init__(self):
        self.items = []
        self._dots = {}

    def clear(self):
        self.items = []

    def add(self, x, y, vx, vy, life, r, color, grav=0.0, alpha=150):
        if len(self.items) < 600:
            self.items.append([x, y, vx, vy, life, life, r, color, grav, alpha])

    def update(self, dt):
        for p in self.items:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[3] += p[8] * dt
            p[4] -= dt
        self.items = [p for p in self.items if p[4] > 0]

    def draw(self, surf, cx, cy):
        for x, y, _, _, life, full, r, color, _, alpha in self.items:
            sx, sy = x - cx, y - cy
            if sx < -40 or sx > W + 40 or sy < -40 or sy > H + 40:
                continue
            k = life / full
            rr = max(2, int(r * (1.6 - 0.6 * k)))
            key = (rr, color)
            d = self._dots.get(key)
            if d is None:
                d = pygame.Surface((rr * 2, rr * 2), pygame.SRCALPHA)
                pygame.draw.circle(d, color + (110,), (rr, rr), rr)
                pygame.draw.circle(d, color + (255,), (rr, rr), max(1, int(rr * 0.6)))
                if len(self._dots) > 400:
                    self._dots.clear()
                self._dots[key] = d
            d.set_alpha(int(alpha * k))
            surf.blit(d, (sx - rr, sy - rr))


# ---------------------------------------------------------------- sound
SCALE = [50, 53, 55, 57, 60, 62, 65, 67, 69, 72, 74, 77, 79, 81, 84]  # D minor pentatonic


class Audio:
    """Everything is synthesised at start-up, so the game ships without sound files."""

    def __init__(self):
        self.ok = False
        self.snd = {}
        self.notes = {}
        self.loops = {}
        self.amb = None
        self.amb_name = None
        self.next_note = 4.0
        if np is None:
            return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 2, 512)
            self.sr, _, self.ch = pygame.mixer.get_init()
            pygame.mixer.set_num_channels(24)
        except Exception:
            return
        self.rng = np.random.default_rng(11)
        self.ok = True
        t = self._t(0.04)
        self.snd["step"] = self._mk(self._noise(0.04, 10) * np.exp(-t * 110), 0.16)
        t = self._t(0.16)
        self.snd["land"] = self._mk(np.sin(2 * np.pi * 72 * t) * np.exp(-t * 26)
                                    + self._noise(0.16, 14) * np.exp(-t * 60) * 0.5, 0.4)
        t = self._t(0.2)
        self.snd["jump"] = self._mk(self._noise(0.2, 5) * np.sin(np.pi * t / 0.2) ** 2, 0.09)
        t = self._t(0.9)
        self.snd["caught"] = self._mk((np.sin(2 * np.pi * 61 * t) + np.sin(2 * np.pi * 65.5 * t)
                                       + self._noise(0.9, 30) * 0.6) * np.exp(-t * 4.5), 0.42)
        t = self._t(2.6)
        self.snd["gust"] = self._mk(self._noise(2.6, 46) * np.sin(np.pi * t / 2.6) ** 1.5, 0.75)
        t = self._t(0.5)
        self.snd["bounce"] = self._mk(np.sin(2 * np.pi * (90 + 120 * np.exp(-t * 9)) * t)
                                      * np.exp(-t * 9), 0.3)

    def _t(self, d):
        return np.arange(int(self.sr * d)) / self.sr

    def _noise(self, d, k):
        n = self.rng.uniform(-1, 1, int(self.sr * d))
        if k > 1:
            n = np.convolve(n, np.ones(k) / k, "same") * math.sqrt(k) * 0.7
        return n

    def _mk(self, a, vol):
        pcm = (np.clip(a * vol, -1, 1) * 32767).astype(np.int16)
        if self.ch > 1:
            pcm = np.column_stack([pcm] * self.ch)
        return pygame.sndarray.make_sound(np.ascontiguousarray(pcm))

    def play(self, name, vol=1.0):
        if self.ok and name in self.snd:
            s = self.snd[name]
            s.set_volume(vol)
            s.play()

    def note(self, midi, vol=1.0):
        if not self.ok:
            return
        s = self.notes.get(midi)
        if s is None:
            f = 440 * 2 ** ((midi - 69) / 12)
            t = self._t(2.4)
            a = sum(amp * np.sin(2 * np.pi * f * n * t) * np.exp(-t * (1.5 + n * 0.9))
                    for n, amp in ((1, 1.0), (2, 0.42), (3, 0.18), (4, 0.07)))
            a *= np.minimum(1, t / 0.006)
            s = self.notes[midi] = self._mk(a, 0.3)
        s.set_volume(vol)
        s.play()

    def ambience(self, theme):
        if not self.ok or theme == self.amb_name:
            return
        self.amb_name = theme
        if self.amb:
            self.amb.fadeout(1200)
        if theme not in self.loops:
            d, x = 5.0, 0.6
            t = self._t(d + x)
            if theme == "laundromat":
                a = self._noise(d + x, 70) * 0.45 + np.sin(2 * np.pi * 100 * t) * 0.05 \
                    + np.sin(2 * np.pi * 50 * t) * 0.06
            elif theme == "market":
                n = self._noise(d + x, 1)
                a = (n - np.convolve(n, np.ones(5) / 5, "same")) * 0.2 + self._noise(d + x, 50) * 0.3
            elif theme == "roofs":
                a = self._noise(d + x, 120) * (0.55 + 0.25 * np.sin(2 * np.pi * t / d))
            else:
                a = self._noise(d + x, 200) * 0.2
            n = int(self.sr * d)
            k = len(a) - n
            ramp = np.linspace(0, 1, k)
            a[:k] = a[:k] * ramp + a[n:n + k] * (1 - ramp)
            self.loops[theme] = self._mk(a[:n], 0.5)
        self.amb = self.loops[theme]
        self.amb.set_volume(0.55)
        self.amb.play(loops=-1, fade_ms=1500)

    def tick(self, dt):
        """Sparse, wandering piano in the distance."""
        if not self.ok:
            return
        self.next_note -= dt
        if self.next_note <= 0:
            self.next_note = random.uniform(2.2, 5.5)
            i = random.randrange(0, 8)
            self.note(SCALE[i] - 12, 0.32)
            if random.random() < 0.35:
                self.note(SCALE[i + 2], 0.16)
