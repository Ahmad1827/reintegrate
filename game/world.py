"""The world: four chapters, the things that live in them, and their painted backdrops."""
import math
import random

import pygame

from . import fx
from .fx import W, H, INK, WARM, mix

LW = 2048  # width of a tiling backdrop layer
GUST_CYCLE = 6.2

THEMES = {
    "laundromat": {"sky": ((36, 54, 58), (62, 90, 86)), "solid": (34, 48, 54), "top": (132, 164, 152)},
    "market": {"sky": ((12, 18, 34), (40, 58, 80)), "solid": (22, 30, 44), "top": (92, 114, 138)},
    "roofs": {"sky": ((38, 40, 82), (232, 150, 124)), "solid": (34, 30, 52), "top": (158, 124, 140)},
    "room": {"sky": ((70, 50, 48), (150, 104, 78)), "solid": (52, 36, 34), "top": (176, 128, 96)},
}
BOOKS = [(126, 70, 62), (62, 92, 100), (150, 122, 78), (84, 76, 110), (70, 104, 82)]


class Solid:
    def __init__(self, rect, kind="box", oneway=False, bouncy=False):
        self.rect = pygame.Rect(rect)
        self.kind = kind
        self.oneway = oneway
        self.bouncy = bouncy
        self.active = True
        self.dx = self.dy = 0
        self.hit_t = 9.0
        self.key = None


class Level:
    def __init__(self, numeral, name, sub, theme, width, spawn, exit_x):
        self.numeral, self.name, self.sub = numeral, name, sub
        self.theme, self.width, self.spawn, self.exit_x = theme, width, spawn, exit_x
        self.solids, self.ents, self.hints = [], [], []
        self.wind = self.rain = False
        self.box(-80, -3000, 80, 4000, "none")
        self.box(width, -3000, 80, 4000, "none")

    def box(self, x, y, w, h, kind="box", **kw):
        q = Solid((x, y, w, h), kind, **kw)
        self.solids.append(q)
        return q

    def floor(self, x1, x2, y=600, kind="floor"):
        return self.box(x1, y, x2 - x1, 500, kind)

    def add(self, *ents):
        self.ents.extend(ents)

    def hint(self, x, y, s):
        self.hints.append((x, y, s))


# =================================================================== entities
class Ent:
    layer = 1  # 0 = drawn behind the solid world, 1 = in front of it

    def update(self, dt, g):
        pass

    def draw(self, surf, cx, cy, g):
        pass


class Vent(Ent):
    """Floor grate that breathes scalding steam on a rhythm."""

    def __init__(self, x, fy, phase=0.0, height=175):
        self.x, self.fy, self.phase, self.height = x, fy, phase, height

    def state(self, t):
        u = (t + self.phase) % 3.4
        return "off" if u < 1.7 else "warn" if u < 2.3 else "on"

    def update(self, dt, g):
        st = self.state(g.t)
        if st == "warn" and random.random() < dt * 16:
            g.parts.add(self.x + random.uniform(-12, 12), self.fy - 4, random.uniform(-10, 10),
                        random.uniform(-90, -50), 0.5, 5, (214, 228, 226), alpha=110)
        elif st == "on":
            for _ in range(2):
                g.parts.add(self.x + random.uniform(-11, 11), self.fy - 6, random.uniform(-26, 26),
                            random.uniform(-540, -380), 0.42, random.uniform(8, 15), (228, 238, 236))
            if g.hand.hit.colliderect(pygame.Rect(self.x - 17, self.fy - self.height, 34, self.height)):
                g.kill()

    def draw(self, surf, cx, cy, g):
        r = pygame.Rect(self.x - 28 - cx, self.fy - 3 - cy, 56, 9)
        pygame.draw.rect(surf, INK, r, border_radius=3)
        for i in range(5):
            pygame.draw.line(surf, (92, 108, 108), (r.x + 8 + i * 10, r.y + 2), (r.x + 8 + i * 10, r.y + 6), 3)


class Puddle(Ent):
    """Water with a live cable in it."""

    def __init__(self, x1, x2, fy, phase=0.0, always=False):
        self.x1, self.x2, self.fy, self.phase, self.always = x1, x2, fy, phase, always

    def state(self, t):
        if self.always:
            return "on"
        u = (t + self.phase) % 3.0
        return "off" if u < 1.5 else "warn" if u < 2.0 else "on"

    def update(self, dt, g):
        if self.state(g.t) == "on" and g.hand.hit.colliderect(
                pygame.Rect(self.x1 + 10, self.fy - 24, self.x2 - self.x1 - 20, 30)):
            g.kill()

    def draw(self, surf, cx, cy, g):
        w = self.x2 - self.x1
        r = pygame.Rect(self.x1 - cx, self.fy - 5 - cy, w, 12)
        if r.right < 0 or r.left > W:
            return
        pygame.draw.ellipse(surf, (30, 52, 72), r)
        pygame.draw.ellipse(surf, (86, 122, 150), r.inflate(-w * 0.3, -6).move(-w * 0.08, -1), 2)
        st = self.state(g.t)
        cable = (self.x1 + w * 0.5 - cx, self.fy - cy)
        pygame.draw.lines(surf, INK, False, [(cable[0] + 40, cable[1] - 600), (cable[0] + 26, cable[1] - 200),
                                             (cable[0] + 4, cable[1] - 40), cable], 4)
        if st == "off":
            return
        n = 2 if st == "warn" else max(3, int(w / 55))
        rnd = random.Random(int(g.t * 24) * 7 + self.x1)
        for _ in range(n):
            x = rnd.uniform(r.left + 10, r.right - 10)
            pts = [(x, r.y + 4)]
            for k in range(1, 4 if st == "on" else 2):
                pts.append((x + rnd.uniform(-16, 16), r.y + 4 - k * rnd.uniform(5, 11)))
            pygame.draw.lines(surf, (200, 240, 255), False, pts, 2)
        if st == "on":
            for gx in range(int(r.left) + 40, int(r.right), 150):
                fx.add_glow(surf, (gx, r.y), 80, (50, 110, 150), 0.7 + 0.3 * rnd.random())


class Sweeper(Ent):
    """A robot vacuum on patrol. Its bumper catches you; its back will carry you."""

    def __init__(self, lv, x1, x2, fy, speed=115):
        self.solid = lv.box(x1, fy - 38, 150, 38, "sweeper")
        self.x1, self.x2, self.fx, self.dir, self.speed = x1, x2 - 150, float(x1), 1, speed

    def update(self, dt, g):
        self.fx += self.dir * self.speed * dt
        if self.fx >= self.x2:
            self.fx, self.dir = float(self.x2), -1
        elif self.fx <= self.x1:
            self.fx, self.dir = float(self.x1), 1
        nx = round(self.fx)
        self.solid.dx = nx - self.solid.rect.x
        self.solid.rect.x = nx
        h = g.hand.rect
        if self.solid.rect.inflate(8, 0).colliderect(h) and h.bottom > self.solid.rect.top + 10:
            g.kill()

    def draw(self, surf, cx, cy, g):
        r = self.solid.rect.move(-cx, -cy)
        pygame.draw.rect(surf, (54, 60, 70), r, border_radius=14)
        pygame.draw.rect(surf, (92, 102, 114), (r.x + 10, r.y + 4, r.w - 20, 7), border_radius=4)
        pygame.draw.rect(surf, INK, r, 3, border_radius=14)
        ex = r.right - 16 if self.dir > 0 else r.left + 16
        pygame.draw.circle(surf, (255, 96, 80), (ex, r.y + 22), 5)
        fx.add_glow(surf, (ex, r.y + 22), 40, (150, 40, 30))
        for k in range(3):
            a = g.t * 14 * self.dir + k * 2.1
            bx = r.centerx + (r.w / 2 - 30) * self.dir
            pygame.draw.line(surf, INK, (bx, r.bottom - 3),
                             (bx + math.cos(a) * 16, r.bottom - 3 + abs(math.sin(a)) * 3), 2)


class Mover(Ent):
    """A hanging tray that glides between two points."""

    def __init__(self, lv, x, y, w, x2, y2, period, phase=0.0):
        self.solid = lv.box(x, y, w, 18, "tray", oneway=True)
        self.a, self.b, self.period, self.phase = (x, y), (x2, y2), period, phase

    def update(self, dt, g):
        u = (1 - math.cos(math.tau * (g.t + self.phase) / self.period)) / 2
        nx, ny = round(fx.lerp(self.a[0], self.b[0], u)), round(fx.lerp(self.a[1], self.b[1], u))
        r = self.solid.rect
        self.solid.dx, self.solid.dy = nx - r.x, ny - r.y
        r.topleft = (nx, ny)

    def draw(self, surf, cx, cy, g):
        r = self.solid.rect.move(-cx, -cy)
        for x in (r.x + 12, r.right - 12):
            pygame.draw.line(surf, INK, (x, r.y), (x + (r.centerx - x) * 0.5, r.y - 900), 3)
        pygame.draw.rect(surf, (116, 92, 72), r, border_radius=4)
        pygame.draw.rect(surf, (160, 130, 100), (r.x + 4, r.y + 3, r.w - 8, 4))
        pygame.draw.rect(surf, INK, r, 3, border_radius=4)


class Neon(Ent):
    """A sign you can stand on - only while it is lit."""

    def __init__(self, lv, x, y, w, off_at, label, color=(255, 110, 150)):
        self.solid = lv.box(x, y, w, 20, "neon")
        self.off_at, self.label, self.color = off_at, label, color

    def state(self, t):
        u = t % GUST_CYCLE
        if self.off_at <= u < self.off_at + 1.0:
            return "off"
        return "flicker" if self.off_at - 0.7 <= u < self.off_at else "lit"

    def update(self, dt, g):
        self.solid.active = self.state(g.t) != "off"

    def draw(self, surf, cx, cy, g):
        r = self.solid.rect.move(-cx, -cy)
        if r.right < -100 or r.left > W + 100:
            return
        st = self.state(g.t)
        lit = st == "lit" or (st == "flicker" and int(g.t * 18) % 3 != 0)
        pygame.draw.line(surf, INK, (r.x + 14, r.y), (r.x + 14, r.y - 700), 3)
        pygame.draw.line(surf, INK, (r.right - 14, r.y), (r.right - 14, r.y - 700), 3)
        if lit:
            pygame.draw.rect(surf, mix(self.color, (255, 255, 255), 0.55), r, border_radius=8)
            pygame.draw.rect(surf, self.color, r, 4, border_radius=8)
            fx.add_glow(surf, r.center, 150, self.color, 0.55)
            fx.text(surf, self.label, 30, mix(self.color, (255, 255, 255), 0.4), (r.centerx, r.y - 28))
        else:
            pygame.draw.rect(surf, (50, 44, 66), r, 3, border_radius=8)
            fx.text(surf, self.label, 30, (60, 52, 78), (r.centerx, r.y - 28))


class Cat(Ent):
    """It dozes, it stirs, it stares. It only sees what moves."""
    layer = 0

    def __init__(self, x, fy, z1=0, z2=0, phase=0.0, sleepy=False):
        self.x, self.fy, self.z1, self.z2, self.phase, self.sleepy = x, fy, z1, z2, phase, sleepy
        self.seen = 0.0
        self.pounce = -1.0
        self.target = (x, fy)

    def state(self, t):
        if self.sleepy:
            return "asleep"
        u = (t + self.phase) % 5.6
        return "asleep" if u < 3.0 else "stir" if u < 3.6 else "awake"

    def update(self, dt, g):
        if self.pounce >= 0:
            self.pounce += dt
            if self.pounce > 0.28:
                g.kill()
                if self.pounce > 1.2:
                    self.pounce, self.seen = -1.0, 0.0
            return
        h = g.hand
        if self.state(g.t) == "awake" and self.z1 < h.cx < self.z2 and not g.dead \
                and (abs(h.vx) > 40 or not h.on_ground):
            self.seen += dt
            if self.seen > 0.16:
                self.pounce, self.target = 0.0, (h.cx, h.bottom)
        else:
            self.seen = 0.0

    def draw(self, surf, cx, cy, g):
        if self.x - cx < -900 or self.x - cx > W + 900:
            return
        st = self.state(g.t)
        x, y = self.x - cx, self.fy - cy
        if self.pounce >= 0:
            u = min(1.0, self.pounce / 0.28)
            x += (self.target[0] - self.x) * u
            y += (self.target[1] - self.fy) * u - math.sin(u * math.pi) * 90
            st = "awake"
        if st == "awake" and self.pounce < 0:
            cone = pygame.Surface((self.z2 - self.z1, 240), pygame.SRCALPHA)
            ex = self.x - self.z1
            pygame.draw.polygon(cone, (250, 220, 130, 26), [(ex, 0), (0, 240), (cone.get_width(), 240)])
            surf.blit(cone, (self.z1 - cx, self.fy - 240 - cy))
        body = (30, 35, 52)
        rim = (128, 142, 172)
        breathe = math.sin(g.t * 1.6) * 3
        sway = math.sin(g.t * (5 if st != "asleep" else 1.2)) * (16 if st != "asleep" else 6)
        tail = [(x + 60, y - 22), (x + 104, y - 14), (x + 132, y - 36 + sway * 0.4), (x + 140, y - 70 + sway)]
        pygame.draw.lines(surf, body, False, tail, 15)
        pygame.draw.circle(surf, body, tail[-1], 7)
        pygame.draw.ellipse(surf, body, (x - 76, y - 150 - breathe, 152, 154 + breathe))
        pygame.draw.arc(surf, rim, (x - 76, y - 150 - breathe, 152, 154), 0.5, 2.6, 3)
        hx, hy = x - 8, y - 176 - breathe
        pygame.draw.circle(surf, body, (hx, hy), 50)
        for s in (-1, 1):
            pygame.draw.polygon(surf, body, [(hx + s * 20, hy - 38), (hx + s * 44, hy - 78), (hx + s * 50, hy - 18)])
        pygame.draw.arc(surf, rim, (hx - 50, hy - 50, 100, 100), 0.6, 2.5, 3)
        for s in (-1, 1):
            e = (hx + s * 20, hy - 2)
            if st == "asleep":
                pygame.draw.arc(surf, rim, (e[0] - 10, e[1] - 6, 20, 12), math.pi, math.tau, 3)
            else:
                hgt = 6 if st == "stir" else 15
                pygame.draw.ellipse(surf, (250, 216, 110), (e[0] - 11, e[1] - hgt / 2, 22, hgt))
                pygame.draw.ellipse(surf, INK, (e[0] - 2.5, e[1] - hgt / 2, 5, hgt))
                fx.add_glow(surf, e, 48, (120, 96, 40), 1.0 if st == "awake" else 0.5)
        if st == "asleep":
            k = (g.t * 0.5) % 1
            fx.text(surf, "z", 30, (150, 164, 190), (hx + 62 + k * 24, hy - 60 - k * 46), alpha=200 * (1 - k), italic=True)


class Checkpoint(Ent):
    def __init__(self, x, fy):
        self.x, self.fy, self.lit, self.t = x, fy, False, 0.0

    def update(self, dt, g):
        if not self.lit and abs(g.hand.cx - self.x) < 60 and abs(g.hand.bottom - self.fy) < 160:
            self.lit = True
            g.checkpoint(self.x, self.fy)
        if self.lit:
            self.t += dt

    def draw(self, surf, cx, cy, g):
        x, y = self.x - cx, self.fy - cy
        if x < -150 or x > W + 150:
            return
        pygame.draw.arc(surf, INK, (x - 9, y - 50, 18, 22), 0, math.pi, 3)
        body = pygame.Rect(x - 12, y - 38, 24, 34)
        pygame.draw.rect(surf, (250, 214, 140) if self.lit else (58, 66, 78), body, border_radius=4)
        pygame.draw.rect(surf, INK, body, 3, border_radius=4)
        pygame.draw.rect(surf, INK, (x - 15, y - 6, 30, 6), border_radius=2)
        if self.lit:
            k = 0.85 + 0.15 * math.sin(g.t * 9) * math.sin(g.t * 5.3)
            fx.add_glow(surf, (x, y - 22), 130 * min(1.0, 0.3 + self.t * 2), (190, 130, 60), k)


class Echo(Ent):
    """Something the hand remembers touching."""

    def __init__(self, x, y, text):
        self.x, self.y, self.text, self.taken, self.t = x, y, text, False, random.uniform(0, 6)

    def update(self, dt, g):
        self.t += dt
        if not self.taken and not g.dead and g.hand.rect.inflate(34, 34).collidepoint(self.x, self.y):
            self.taken = True
            g.collect(self)

    def draw(self, surf, cx, cy, g):
        if self.taken:
            return
        x, y = self.x - cx, self.y - cy + math.sin(self.t * 2.2) * 6
        if x < -80 or x > W + 80:
            return
        fx.add_glow(surf, (x, y), 64, (200, 150, 70), 0.8 + 0.2 * math.sin(self.t * 3))
        pygame.draw.circle(surf, (255, 236, 190), (x, y), 6)
        for k in range(2):
            a = self.t * 1.7 + k * math.pi
            pygame.draw.circle(surf, (255, 214, 150), (x + math.cos(a) * 17, y + math.sin(a) * 7), 2)


class Decor(Ent):
    layer = 0

    def __init__(self, kind, x, y):
        self.kind, self.x, self.y = kind, x, y

    def draw(self, surf, cx, cy, g):
        x, y = self.x - cx, self.y - cy
        if x < -1600 or x > W + 400:
            return
        k = self.kind
        if k == "exit":
            door = pygame.Rect(x - 50, y - 260, 100, 260)
            pygame.draw.rect(surf, (252, 222, 160), door)
            pygame.draw.rect(surf, INK, door, 5)
            fx.add_glow(surf, (x, y - 130), 300, (170, 120, 60), 0.9 + 0.1 * math.sin(g.t * 2))
        elif k == "lamp":
            pygame.draw.line(surf, (10, 14, 22), (x, y), (x, y - 520), 9)
            pygame.draw.line(surf, (10, 14, 22), (x, y - 520), (x + 56, y - 540), 7)
            pygame.draw.ellipse(surf, (255, 226, 170), (x + 38, y - 540, 40, 16))
            fx.add_glow(surf, (x + 58, y - 520), 260, (150, 104, 54))
            fx.add_glow(surf, (x + 58, y - 60), 200, (60, 40, 20))
        elif k == "legs":  # furniture legs under a seat: x = left, y = seat top, kind-specific width
            for lx in (x + 16, x + self.w - 16):
                pygame.draw.line(surf, (60, 40, 36), (lx, y + 10), (lx, 600 - cy), 14)
                pygame.draw.line(surf, INK, (lx - 8, y + 10), (lx - 8, 600 - cy), 2)
        elif k == "piano":
            pygame.draw.rect(surf, (26, 18, 20), (x - 30, y - 170, 1360, 170))
            pygame.draw.rect(surf, INK, (x - 30, y - 170, 1360, 170), 4)
            pygame.draw.line(surf, (150, 112, 70), (x - 10, y - 60), (x + 1310, y - 60), 2)
            desk = pygame.Rect(x + 420, y - 290, 460, 130)
            pygame.draw.rect(surf, (36, 25, 26), desk)
            pygame.draw.rect(surf, INK, desk, 4)
            for sx in (desk.x + 40, desk.x + 240):
                page = pygame.Rect(sx, desk.y + 14, 180, 104)
                pygame.draw.rect(surf, (236, 226, 204), page)
                for ly in range(page.y + 16, page.bottom - 8, 16):
                    pygame.draw.line(surf, (150, 140, 124), (page.x + 12, ly), (page.right - 12, ly), 1)
                    for nx in range(page.x + 22, page.right - 14, 26):
                        pygame.draw.circle(surf, INK, (nx, ly - ((nx * 7 + ly) % 9) + 3), 3)
            for i in range(24):
                if i % 7 in (0, 1, 3, 4, 5):
                    pygame.draw.rect(surf, (8, 8, 12), (x + i * 50 + 35, y - 34, 30, 34), border_radius=3)
                    pygame.draw.rect(surf, (84, 84, 100), (x + i * 50 + 35, y - 34, 30, 34), 2, border_radius=3)


# =================================================================== drawing solids
def draw_solid(surf, q, cx, cy, T, t):
    k = q.kind
    if k in ("none", "sweeper", "tray", "neon"):
        return
    r = q.rect.move(-cx, -cy)
    if r.right < -20 or r.left > W + 20 or r.top > H or r.bottom < 0:
        return
    if k in ("floor", "roof"):
        v = r.clip(pygame.Rect(-10, -10, W + 20, H + 20))
        pygame.draw.rect(surf, T["solid"], v)
        if k == "roof":
            for by in range(r.y + 36, min(r.bottom, H), 30):
                pygame.draw.line(surf, mix(T["solid"], (0, 0, 0), 0.25), (v.left, by), (v.right, by), 2)
            pygame.draw.rect(surf, T["top"], (r.x - 8, r.y, r.w + 16, 12))
            pygame.draw.rect(surf, INK, (r.x - 8, r.y, r.w + 16, 12), 3)
            pygame.draw.line(surf, INK, (r.x, r.y + 12), (r.x, min(r.bottom, H)), 3)
            pygame.draw.line(surf, INK, (r.right - 2, r.y + 12), (r.right - 2, min(r.bottom, H)), 3)
        else:
            pygame.draw.rect(surf, T["top"], (v.x, r.y, v.w, 7))
            pygame.draw.rect(surf, INK, r, 3)
            for x in range(q.rect.x // 96 * 96 + 96, q.rect.right, 96):
                if 0 < x - cx < W:
                    pygame.draw.line(surf, mix(T["solid"], (0, 0, 0), 0.3), (x - cx, r.y + 8), (x - cx, r.y + 22), 2)
        return
    if k == "crate":
        pygame.draw.rect(surf, (124, 94, 70), r)
        for py in range(r.y + 26, r.bottom - 6, 28):
            pygame.draw.line(surf, (92, 68, 52), (r.x + 3, py), (r.right - 4, py), 3)
        pygame.draw.line(surf, (146, 112, 84), (r.x + 4, r.y + 5), (r.right - 5, r.y + 5), 3)
    elif k == "box":
        pygame.draw.rect(surf, (172, 84, 74), r)
        pygame.draw.rect(surf, (232, 224, 206), (r.x, r.y + r.h * 0.34, r.w, r.h * 0.3))
        pygame.draw.circle(surf, (92, 132, 142), (r.centerx, r.y + r.h * 0.49), r.h * 0.11)
    elif k == "machine":
        pygame.draw.rect(surf, (170, 186, 182), r)
        n = max(1, round(r.w / 165))
        cw = r.w / n
        for i in range(n):
            c = (r.x + cw * (i + 0.5), r.y + r.h * 0.6)
            rad = min(cw, r.h) * 0.3
            pygame.draw.circle(surf, (118, 136, 134), c, rad + 9)
            pygame.draw.circle(surf, (34, 52, 60), c, rad)
            pygame.draw.arc(surf, (120, 160, 170), (c[0] - rad * 0.7, c[1] - rad * 0.7, rad * 1.4, rad * 1.4), 0.7, 2.2, 3)
            pygame.draw.circle(surf, INK, c, rad + 9, 3)
            if i:
                pygame.draw.line(surf, INK, (r.x + cw * i, r.y), (r.x + cw * i, r.bottom), 3)
            if r.h > 150:
                pygame.draw.rect(surf, (130, 150, 148), (r.x + cw * i + 12, r.y + 12, cw - 24, 26), border_radius=4)
                pygame.draw.circle(surf, WARM, (r.x + cw * i + 30, r.y + 25), 5)
    elif k in ("awning", "tarp"):
        dip = math.sin(q.hit_t * 18) * math.exp(-q.hit_t * 6) * 9 if q.hit_t < 2 else 0
        r = r.move(0, dip)
        if k == "awning":
            for i, sx in enumerate(range(r.x, r.right, 26)):
                col = (196, 92, 78) if i % 2 else (230, 218, 198)
                wd = min(26, r.right - sx)
                pygame.draw.rect(surf, col, (sx, r.y, wd, r.h + 8))
                pygame.draw.circle(surf, col, (sx + wd / 2, r.bottom + 8), wd / 2)
        else:
            pygame.draw.rect(surf, (64, 104, 112), (r.x, r.y, r.w, r.h + 6))
            for sx in range(r.x, r.right - 20, 40):
                pygame.draw.polygon(surf, (50, 84, 92), [(sx, r.bottom + 6), (sx + 40, r.bottom + 6), (sx + 20, r.bottom + 22)])
        pygame.draw.line(surf, INK, r.topleft, r.topright, 4)
        for px in (r.x + 6, r.right - 6):
            pygame.draw.line(surf, INK, (px, r.y), (px, 600 - cy), 5)
        return
    elif k == "wood":
        pygame.draw.rect(surf, (112, 76, 58), r, border_radius=5)
        pygame.draw.rect(surf, (156, 110, 82), (r.x + 4, r.y + 3, r.w - 8, 5), border_radius=2)
        pygame.draw.rect(surf, INK, r, 3, border_radius=5)
        return
    elif k == "book":
        pygame.draw.rect(surf, BOOKS[(q.rect.x // 10 + q.rect.y) % len(BOOKS)], r)
        pygame.draw.rect(surf, (232, 222, 200), (r.right - 12, r.y + 5, 12, r.h - 10))
        for lx in (r.x + 18, r.x + 30):
            pygame.draw.line(surf, (236, 206, 150), (lx, r.y + 4), (lx, r.bottom - 5), 2)
    elif k == "key":
        down = 3 if q.hit_t < 0.25 else 0
        r = r.move(0, down)
        pygame.draw.rect(surf, (206, 198, 180) if down else (238, 232, 216), r)
        pygame.draw.rect(surf, INK, r, 2)
        return
    elif k == "pianocase":
        pygame.draw.rect(surf, (30, 21, 22), r)
        pygame.draw.line(surf, (60, 42, 40), (r.x, r.y + 30), (r.right, r.y + 30), 3)
    elif k == "chimney":
        pygame.draw.rect(surf, (124, 68, 62), r)
        for by in range(r.y + 22, r.bottom, 18):
            pygame.draw.line(surf, (90, 48, 46), (r.x, by), (r.right, by), 2)
        pygame.draw.rect(surf, (160, 100, 90), (r.x - 6, r.y, r.w + 12, 12))
        pygame.draw.rect(surf, INK, (r.x - 6, r.y, r.w + 12, 12), 3)
    elif k == "tank":
        pygame.draw.rect(surf, (72, 80, 104), r, border_radius=10)
        for bx in range(r.x + 26, r.right - 10, 34):
            pygame.draw.line(surf, (52, 58, 80), (bx, r.y + 4), (bx, r.bottom - 4), 3)
        pygame.draw.rect(surf, INK, r, 3, border_radius=10)
        return
    else:
        pygame.draw.rect(surf, T["solid"], r)
    pygame.draw.rect(surf, INK, r, 3)


# =================================================================== chapters
def _level1():
    L = Level("I", "The Laundromat", "2:14 a.m.", "laundromat", 6500, (170, 600), 6390)
    L.floor(-200, 2300)
    L.floor(2460, 4200)
    L.floor(4900, 6700)
    L.hint(330, 452, "A  D   -   or move your hand left and right")
    L.hint(700, 400, "SPACE   -   or raise your hand")
    L.box(600, 530, 130, 70, "box")
    L.box(900, 490, 150, 110, "crate")
    L.hint(1090, 452, "S   -   or close your fist")
    L.box(1250, 250, 330, 314, "machine")          # crawl underneath
    L.add(Echo(975, 425, "Warm laundry, straight from the drum."),
          Checkpoint(1690, 600), Vent(1880, 600, 0.0), Vent(2090, 600, 1.7))
    sweep = Sweeper(L, 2640, 3400, 600)
    L.hint(3020, 430, "some things will carry you")
    L.box(3400, 430, 300, 170, "machine")           # too tall to jump - ride the sweeper
    L.add(sweep, Echo(3550, 372, "A coin, pressed into your palm for the machine."),
          Checkpoint(3830, 600), Vent(4030, 600, 0.8))
    L.add(Mover(L, 4230, 590, 150, 4720, 590, 6.0),
          Echo(4550, 500, "Chalk dust. Scales, over and over."),
          Checkpoint(5000, 600), Vent(5170, 600, 0.0), Vent(5350, 600, 1.1), Vent(5530, 600, 2.2))
    L.box(5760, 520, 130, 80, "crate")
    L.box(5890, 450, 130, 150, "crate")
    L.add(Echo(5955, 388, "The lid of the piano - heavier than it looked."), Decor("exit", 6390, 600))
    return L


def _level2():
    L = Level("II", "Night Market", "3:40 a.m.", "market", 7700, (170, 600), 7560)
    L.rain = True
    L.floor(-200, 7900)
    for x in (260, 1380, 2480, 3700, 5080, 6460, 7300):
        L.add(Decor("lamp", x, 600))
    L.box(450, 540, 120, 60, "crate")
    L.box(570, 480, 120, 120, "crate")
    L.box(770, 430, 250, 14, "awning", oneway=True, bouncy=True)
    L.box(1090, 250, 210, 30, "wood")
    L.add(Echo(1195, 196, "Rain on the back of the hand, counting time."), Checkpoint(1420, 600))
    L.hint(1660, 400, "it only sees what moves")
    L.add(Cat(1930, 600, 1560, 2330), Checkpoint(2480, 600),
          Puddle(2700, 2860, 600, 0.0), Puddle(3090, 3250, 600, 1.0), Puddle(3430, 3590, 600, 2.0),
          Echo(3340, 468, "A paper bag of chestnuts, too hot to hold."), Checkpoint(3740, 600))
    L.box(3880, 520, 110, 80, "crate")
    L.add(Puddle(4000, 5010, 600, always=True))     # the flooded stretch: cross on the tarps
    L.box(4020, 440, 220, 14, "tarp", oneway=True)
    L.box(4340, 410, 220, 14, "tarp", oneway=True)
    L.box(4660, 440, 220, 14, "tarp", oneway=True)
    L.add(Echo(4450, 318, "Someone's fingers, laced through yours at a crossing."), Checkpoint(5110, 600),
          Cat(5800, 600, 5320, 6300, 2.4), Puddle(5560, 5690, 600, 0.6),
          Checkpoint(6470, 600), Echo(6700, 500, "The cold rail of the last tram."))
    L.box(6640, 540, 120, 60, "crate")
    L.add(Decor("exit", 7560, 600))
    return L


def _level3():
    L = Level("III", "Rooftops", "5:55 a.m.", "roofs", 7100, (170, 600), 6930)
    L.wind = True
    L.floor(-200, 900, 600, "roof")
    L.hint(470, 440, "when the wind comes, hold on  -  S, or close your fist")
    L.floor(1050, 1750, 560, "roof")
    L.box(1400, 480, 90, 80, "chimney")
    L.add(Echo(1445, 425, "Wind through open fingers from a car window."))
    L.floor(1900, 2430, 600, "roof")
    L.add(Checkpoint(2010, 600))
    L.hint(2230, 430, "lit means solid")
    L.add(Neon(L, 2520, 560, 150, 0.5, "OPEN"), Neon(L, 2760, 520, 150, 1.4, "ALL", (120, 220, 255)),
          Neon(L, 3000, 560, 150, 2.3, "NIGHT"),
          Echo(2835, 440, "A key turned twice. A door you knew by feel."))
    L.floor(3240, 3840, 600, "roof")
    L.add(Checkpoint(3320, 600), Mover(L, 3870, 600, 160, 3870, 380, 7.0))
    L.floor(4100, 4800, 380, "roof")
    L.box(4400, 290, 160, 90, "tank")
    L.add(Echo(4480, 236, "Page corners, softened from turning."))
    L.floor(4950, 5500, 440, "roof")
    L.add(Checkpoint(5080, 440),
          Neon(L, 5590, 420, 150, 0.6, "PIANO", (255, 190, 110)), Neon(L, 5830, 400, 150, 1.9, "BAR", (255, 190, 110)))
    L.floor(6070, 7300, 440, "roof")
    L.add(Decor("exit", 6930, 440))
    return L


def _level4():
    L = Level("IV", "The Room", "sunrise", "room", 3460, (170, 600), 10 ** 9)
    L.floor(-200, 3700)
    L.add(Cat(300, 600, sleepy=True))
    L.box(520, 560, 300, 40, "book")
    L.box(600, 520, 260, 40, "book")
    L.box(680, 484, 200, 36, "book")
    for x, y, w in ((980, 420, 320), (1420, 380, 220), (1760, 340, 260)):
        L.box(x, y, w, 24, "wood", oneway=True)
        d = Decor("legs", x, y)
        d.w = w
        L.add(d)
    L.add(Echo(1140, 360, "Ivory, cool at first. Then not."),
          Echo(1530, 318, "A metronome, stopped with one finger."),
          Echo(1890, 272, "Applause is a thing hands do for each other."),
          Decor("piano", 2160, 290))
    for i in range(24):
        L.box(2160 + i * 50, 290, 50, 26, "key").key = i
    L.box(2160, 316, 1300, 284, "pianocase")
    L.box(3360, 236, 100, 80, "pianocase")
    L.end_x = 2160 + 23 * 50 + 10
    return L


BUILDERS = [_level1, _level2, _level3, _level4]


def build(i):
    return BUILDERS[i]()


def total_echoes():
    return sum(isinstance(e, Echo) for b in BUILDERS for e in b().ents)


# =================================================================== backdrops
def _layer():
    return pygame.Surface((LW, H), pygame.SRCALPHA)


def _skyline(rng, col, lit, hr, lit_p, antenna=False):
    s = _layer()
    x = -30
    while x < LW:
        bw, bh = rng.randint(90, 220), rng.randint(*hr)
        top = H - bh
        pygame.draw.rect(s, col, (x, top, bw, bh))
        if rng.random() < 0.45:
            pygame.draw.rect(s, col, (x + rng.randint(8, bw // 2), top - rng.randint(14, 36), rng.randint(24, 60), 40))
        if antenna and rng.random() < 0.5:
            ax = x + rng.randint(10, bw - 10)
            pygame.draw.line(s, col, (ax, top), (ax, top - rng.randint(30, 80)), 3)
        for wy in range(top + 18, H, 36):
            for wx in range(x + 12, x + bw - 18, 28):
                p = rng.random()
                if p < lit_p:
                    pygame.draw.rect(s, lit, (wx, wy, 12, 18))
                elif p < 0.45:
                    pygame.draw.rect(s, mix(col, (255, 255, 255), 0.07), (wx, wy, 12, 18))
        x += bw + rng.randint(0, 26)
    return s.convert_alpha()


def _halo(s, pos, r, col, a):
    h = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
    for i in range(r, 0, -3):
        pygame.draw.circle(h, col + (int(a * (1 - i / r) ** 2),), (r, r), i)
    s.blit(h, (pos[0] - r, pos[1] - r))


def build_bg(theme, seed=1):
    """Returns (sky, back layers [(surface, parallax)], front layers)."""
    rng = random.Random(seed)
    T = THEMES[theme]
    sky = fx.vgrad(W, H, *T["sky"])
    back, front = [], []
    if theme == "market":
        fx.add_glow(sky, (980, 150), 240, (50, 60, 84))
        pygame.draw.circle(sky, (206, 214, 226), (980, 150), 26)
        back.append((_skyline(rng, (24, 36, 58), (150, 120, 84), (300, 560), 0.08), 0.1))
        back.append((_skyline(rng, (18, 27, 44), (214, 160, 96), (380, 660), 0.10), 0.25))
        back.append((_skyline(rng, (12, 19, 32), (240, 186, 110), (250, 480), 0.06), 0.5))
        s = _layer()
        for x0 in range(0, LW, 512):
            pts = [(x0 + i * 32, 130 + 74 * (1 - ((i - 8) / 8) ** 2)) for i in range(17)]
            pygame.draw.lines(s, (8, 12, 20), False, pts, 2)
            for i, p in enumerate(pts[1:-1]):
                col = (255, 214, 150) if i % 3 else (255, 150, 130)
                _halo(s, p, 14, col, 90)
                pygame.draw.circle(s, col, (p[0], p[1] + 4), 4)
        back.append((s.convert_alpha(), 0.75))
        s = _layer()
        for x in (300, 1340):
            pygame.draw.rect(s, (7, 9, 15), (x, 0, 18, H))
            pygame.draw.rect(s, (7, 9, 15), (x - 12, 560, 42, 160))
        front.append((s.convert_alpha(), 1.4))
    elif theme == "roofs":
        fx.add_glow(sky, (900, 600), 440, (110, 56, 40))
        for _ in range(7):
            c = pygame.Surface((rng.randint(300, 620), rng.randint(14, 30)), pygame.SRCALPHA)
            pygame.draw.ellipse(c, (255, 190, 170, 46), c.get_rect())
            sky.blit(c, (rng.randint(-100, W - 200), rng.randint(130, 470)))
        back.append((_skyline(rng, (96, 76, 122), (255, 210, 150), (150, 300), 0.03, True), 0.08))
        back.append((_skyline(rng, (68, 56, 102), (255, 210, 150), (100, 240), 0.05, True), 0.2))
        back.append((_skyline(rng, (46, 40, 78), (255, 206, 140), (40, 170), 0.06, True), 0.42))
        s = _layer()
        for x in (500, 1500):
            pygame.draw.rect(s, (16, 14, 30), (x, 60, 9, H))
            for k in range(4):
                pygame.draw.line(s, (16, 14, 30), (x - 46 + k * 6, 90 + k * 30), (x + 54 - k * 6, 90 + k * 30), 4)
        front.append((s.convert_alpha(), 1.4))
    elif theme == "laundromat":
        s = _layer()
        for x in range(120, LW, 683):
            win = pygame.Rect(x, 70, 430, 320)
            pygame.draw.rect(s, (14, 22, 36), win)
            for _ in range(16):
                p = (rng.randint(win.x + 10, win.right - 10), rng.randint(win.y + 120, win.bottom - 10))
                pygame.draw.circle(s, rng.choice([(240, 190, 120), (150, 170, 200), (220, 110, 100)]), p, rng.choice([2, 2, 3]))
            pygame.draw.rect(s, (92, 120, 114), win, 9)
            pygame.draw.line(s, (92, 120, 114), win.midtop, win.midbottom, 7)
        back.append((s.convert_alpha(), 0.4))
        s = _layer()
        for x in range(0, LW, 256):
            body = pygame.Rect(x + 16, 250, 224, 480)
            pygame.draw.rect(s, (50, 74, 76), body, border_radius=10)
            pygame.draw.rect(s, (40, 60, 64), body, 5, border_radius=10)
            pygame.draw.circle(s, (64, 92, 92), (x + 128, 460), 84)
            pygame.draw.circle(s, (28, 44, 50), (x + 128, 460), 68)
            pygame.draw.arc(s, (70, 104, 108), (x + 80, 412, 96, 96), 0.7, 2.2, 4)
            pygame.draw.rect(s, (42, 62, 66), (x + 36, 272, 184, 34), border_radius=6)
            if x % 512 == 0:
                _halo(s, (x + 128, 40), 150, (200, 240, 220), 60)
                pygame.draw.rect(s, (220, 244, 228), (x + 30, 34, 196, 10), border_radius=5)
        back.append((s.convert_alpha(), 0.72))
    else:  # room
        s = _layer()
        for x in range(0, LW, 64):
            pygame.draw.line(s, (255, 220, 190, 16), (x, 0), (x, H), 22)
        for x in (760, 1784):
            win = pygame.Rect(x, 60, 430, 400)
            s.blit(fx.vgrad(win.w, win.h, (140, 150, 200), (255, 196, 130)), win)
            pygame.draw.circle(s, (255, 240, 200), (win.centerx + 60, win.bottom - 70), 44)
            pygame.draw.rect(s, (84, 56, 50), win, 12)
            pygame.draw.line(s, (84, 56, 50), win.midtop, win.midbottom, 8)
            pygame.draw.line(s, (84, 56, 50), win.midleft, win.midright, 8)
            for sx, d in ((win.x - 60, 1), (win.right + 60, -1)):
                pygame.draw.polygon(s, (120, 62, 60), [(sx, 30), (sx + d * 110, 30), (sx + d * 70, 520), (sx, 560)])
            _halo(s, (win.centerx, win.centery + 60), 380, (255, 200, 130), 50)
        back.append((s.convert_alpha(), 0.3))
        s = _layer()
        for x in (60, 1100):
            shelf = pygame.Rect(x, 150, 330, 580)
            pygame.draw.rect(s, (46, 31, 31), shelf)
            for sy in range(shelf.y + 20, H, 112):
                bx = shelf.x + 14
                while bx < shelf.right - 30:
                    bw, bh = rng.randint(14, 30), rng.randint(60, 92)
                    pygame.draw.rect(s, mix(rng.choice(BOOKS), (46, 31, 31), 0.45), (bx, sy + 96 - bh, bw, bh))
                    bx += bw + rng.choice([2, 2, 3, 14])
                pygame.draw.rect(s, (62, 42, 40), (shelf.x, sy + 96, shelf.w, 10))
        lx = 640
        pygame.draw.line(s, (40, 28, 28), (lx, 720), (lx, 300), 8)
        pygame.draw.polygon(s, (226, 176, 120), [(lx - 50, 310), (lx + 50, 310), (lx + 30, 230), (lx - 30, 230)])
        _halo(s, (lx, 300), 220, (255, 200, 130), 70)
        back.append((s.convert_alpha(), 0.65))
    return sky.convert(), back, front
