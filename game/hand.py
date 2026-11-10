"""The player: a hand that walks on its fingertips. Physics + procedural animation."""
import math

import pygame

from . import fx
from .fx import INK, SKIN, SKIN_D, SKIN_L, CUFF, clamp

GRAV = 2300.0
RUN = 330.0
CRAWL = 150.0
JUMP = 830.0
STRIDE = 34.0

# index, middle, ring, pinky, thumb (all in "facing right" space)
HOME = [40, 27, 13, -1, -25]                       # where each fingertip rests, from centre
BASE = [(22, 3), (19, 0), (13, 2), (6, 4), (-8, 8)]  # where each finger leaves the palm
LEN = [(25, 30), (27, 31), (24, 28), (20, 24), (19, 22)]
WIDTH = [11, 12, 11, 9, 12]
AIR = [(48, -6), (40, 8), (22, 16), (4, 15), (-28, 4)]
ORDER = [(3, SKIN_D), (2, SKIN_D), None, (1, SKIN), (0, SKIN), (4, SKIN_L)]  # None = palm


class Hand:
    W = 58
    HS = 44   # standing height
    HC = 26   # crouched (fist) height

    def __init__(self, x, bottom):
        self.w, self.h = self.W, self.HS
        self.x, self.y = x - self.w / 2, float(bottom - self.h)
        self.vx = self.vy = 0.0
        self.facing = 1
        self.on_ground = False
        self.ground = None
        self.crouch = False
        self.coyote = self.buffer = 0.0
        self.squash = 0.0
        self.lift = 30.0
        self.t = 0.0
        self.landed = self.jumped = self.stepped = self.bounced = False
        self.feet = [{"x": x + HOME[i], "y": float(bottom), "fx": 0.0, "fy": 0.0,
                      "tx": 0.0, "ty": 0.0, "t": -1.0} for i in range(5)]

    # ------------------------------------------------------------ geometry
    @property
    def cx(self):
        return self.x + self.w / 2

    @property
    def bottom(self):
        return self.y + self.h

    @property
    def rect(self):
        return pygame.Rect(round(self.x), round(self.y), self.w, self.h)

    @property
    def hit(self):
        """Forgiving hitbox used for hazards."""
        return self.rect.inflate(-16, -8)

    def _set_h(self, h):
        b = self.bottom
        self.h = h
        self.y = b - h
        self.crouch = h == self.HC

    def _can_stand(self, solids):
        test = pygame.Rect(round(self.x) + 2, round(self.bottom) - self.HS, self.w - 4, self.HS - 2)
        return not any(test.colliderect(q.rect) for q in solids if not q.oneway)

    # ------------------------------------------------------------ physics
    def update(self, dt, inp, level, gust=False):
        self.t += dt
        self.landed = self.jumped = self.stepped = self.bounced = False
        solids = [q for q in level.solids if q.active]

        g = self.ground
        if g is not None and self.on_ground and g.active and (g.dx or g.dy):
            self.x += g.dx
            self.y += g.dy
            for f in self.feet:
                for k in ("x", "fx", "tx"):
                    f[k] += g.dx
                for k in ("y", "fy", "ty"):
                    f[k] += g.dy

        want = inp.crouch and self.on_ground
        if want and not self.crouch:
            self._set_h(self.HC)
        elif not want and self.crouch and self._can_stand(solids):
            self._set_h(self.HS)

        target = inp.move * (CRAWL if self.crouch else RUN)
        if gust and not (self.crouch and self.on_ground):
            target -= 250 if self.on_ground else 400
        acc = (2800 if self.on_ground else 1800) * dt
        self.vx += clamp(target - self.vx, -acc, acc)
        if abs(inp.move) > 0.1:
            self.facing = 1 if inp.move > 0 else -1

        self.buffer = 0.12 if inp.jump_pressed else max(0.0, self.buffer - dt)
        self.coyote = 0.1 if self.on_ground else max(0.0, self.coyote - dt)
        if self.buffer > 0 and self.coyote > 0:
            if self.crouch and self._can_stand(solids):
                self._set_h(self.HS)
            if not self.crouch:
                self.vy = -JUMP
                self.buffer = self.coyote = 0.0
                self.on_ground, self.ground, self.jumped = False, None, True
        if self.vy < 0 and not inp.jump_held:
            self.vy += GRAV * 1.6 * dt
        self.vy = min(self.vy + GRAV * dt, 1500.0)

        # horizontal
        self.x += self.vx * dt
        r = pygame.Rect(math.ceil(self.x) if self.vx > 0 else math.floor(self.x),
                        math.floor(self.y), self.w, self.h)
        for q in solids:
            if q.oneway or not r.colliderect(q.rect):
                continue
            if self.vx > 0 or (self.vx == 0 and r.centerx < q.rect.centerx):
                self.x = float(q.rect.left - self.w)
            else:
                self.x = float(q.rect.right)
            self.vx = 0.0
            r.x = int(self.x)

        # vertical
        prev_bottom = self.bottom
        self.y += self.vy * dt
        r = pygame.Rect(round(self.x), math.ceil(self.y) if self.vy >= 0 else math.floor(self.y),
                        self.w, self.h)
        was = self.on_ground
        self.on_ground, self.ground = False, None
        for q in solids:
            if not r.colliderect(q.rect):
                continue
            if self.vy >= 0:
                if q.oneway and prev_bottom > q.rect.top + 8 + abs(q.dy) * 2:
                    continue
                self.y = float(q.rect.top - self.h)
                if q.bouncy and self.vy > 250:
                    self.vy = -1060.0
                    self.bounced = True
                    q.hit_t = 0.0
                else:
                    self.vy = 0.0
                    self.on_ground, self.ground = True, q
            elif not q.oneway:
                self.y = float(q.rect.bottom)
                self.vy = 0.0
            r.y = int(self.y)
        if self.on_ground and not was:
            self.landed = True
            self.squash = 1.0
        self.squash = max(0.0, self.squash - dt * 5)
        self._feet(dt)

    # ------------------------------------------------------------ gait
    def _feet(self, dt):
        cx, bottom, face = self.cx, self.bottom, self.facing
        spread = 0.72 if self.crouch else 1.0
        self.lift += ((15.0 if self.crouch else 30.0) - self.lift) * min(1.0, dt * 16)
        stepping = sum(1 for f in self.feet if f["t"] >= 0)
        for i, f in enumerate(self.feet):
            home = cx + face * HOME[i] * spread
            if not self.on_ground:
                ax, ay = AIR[i]
                reach = clamp(self.vy / 900.0, -1.0, 1.0)
                tx = cx + face * ax * (1.0 - 0.15 * reach)
                ty = bottom - 20 + ay + reach * 8
                k = min(1.0, dt * 20)
                f["x"] += (tx - f["x"]) * k
                f["y"] += (ty - f["y"]) * k
                f["t"] = -1.0
                continue
            if f["t"] >= 0:
                f["t"] += dt / 0.085
                f["tx"] = home + self.vx * 0.07 + (STRIDE * 0.8 * (1 if self.vx > 0 else -1)
                                                   if abs(self.vx) > 20 else 0)
                f["ty"] = bottom
                u = min(1.0, f["t"])
                f["x"] = fx.lerp(f["fx"], f["tx"], u)
                f["y"] = fx.lerp(f["fy"], f["ty"], u) - math.sin(math.pi * u) * 11
                if u >= 1.0:
                    f["t"] = -1.0
                    self.stepped = True
                continue
            f["y"] = bottom
            lag = abs(f["x"] - home)
            if lag > STRIDE * 2.2 or (lag > STRIDE and stepping < 3) or \
                    (lag > 5 and abs(self.vx) < 12 and stepping < 2):
                f["t"], f["fx"], f["fy"] = 0.0, f["x"], f["y"]
                stepping += 1

    # ------------------------------------------------------------ drawing
    @staticmethod
    def _ik(bx, by, tx, ty, l1, l2):
        dx, dy = tx - bx, ty - by
        d = math.hypot(dx, dy) or 0.001
        dc = clamp(d, abs(l1 - l2) + 0.5, l1 + l2 - 0.5)
        tx, ty = bx + dx / d * dc, by + dy / d * dc
        a = math.acos(clamp((l1 * l1 + dc * dc - l2 * l2) / (2 * l1 * dc), -1, 1))
        base = math.atan2(dy, dx)
        j1 = (bx + math.cos(base - a) * l1, by + math.sin(base - a) * l1)
        j2 = (bx + math.cos(base + a) * l1, by + math.sin(base + a) * l1)
        return (j1 if j1[1] < j2[1] else j2), (tx, ty)

    @staticmethod
    def _limb(surf, a, b, w, col):
        pygame.draw.line(surf, col, a, b, w)
        pygame.draw.circle(surf, col, a, w // 2)
        pygame.draw.circle(surf, col, b, w // 2)

    def draw(self, surf, camx, camy):
        face = self.facing
        cx = self.cx - camx
        bottom = self.bottom - camy
        moving = self.on_ground and abs(self.vx) > 30
        bob = math.sin(self.t * 22) * 1.6 if moving else math.sin(self.t * 2.2) * 1.0
        py = bottom - self.lift + self.squash * 7 + bob
        tilt = clamp(self.vx / RUN, -1, 1) * 0.10 * face
        if not self.on_ground:
            tilt += clamp(self.vy / 1500.0, -0.6, 0.6) * 0.5
        ca, sa = math.cos(tilt), math.sin(tilt)
        sq = 1.0 - self.squash * 0.18

        def P(lx, ly):
            ly *= sq
            return (cx + face * (lx * ca - ly * sa), py + lx * sa + ly * ca)

        if self.on_ground:
            sh = pygame.Surface((96, 14), pygame.SRCALPHA)
            pygame.draw.ellipse(sh, (0, 0, 0, 70), sh.get_rect())
            surf.blit(sh, (cx - 48 - face * 6, bottom - 6))

        limbs = []
        for i in range(5):
            b = P(*BASE[i])
            f = self.feet[i]
            l1, l2 = LEN[i]
            j, tip = self._ik(b[0], b[1], f["x"] - camx, f["y"] - camy - 4, l1, l2)
            limbs.append((b, j, tip))

        for item in ORDER:
            if item is None:
                self._palm(surf, P)
                continue
            i, col = item
            b, j, tip = limbs[i]
            w = WIDTH[i]
            self._limb(surf, b, j, w + 5, INK)
            self._limb(surf, j, tip, w + 3, INK)
            self._limb(surf, b, j, w, col)
            self._limb(surf, j, tip, w - 2, col)
            pygame.draw.circle(surf, SKIN_L, (tip[0] + face * 1.5, tip[1] - 2), 2.5)  # nail

    def _palm(self, surf, P):
        w0, w1 = P(-20, 3), P(-40, 6)
        self._limb(surf, w0, w1, 27, INK)
        self._limb(surf, w0, w1, 22, SKIN_D)
        c0, c1 = P(-37, 6), P(-45, 7)
        pygame.draw.line(surf, INK, c0, c1, 31)
        pygame.draw.line(surf, CUFF, P(-38, 6), P(-44, 7), 26)
        pygame.draw.line(surf, (176, 172, 160), P(-41, -6), P(-41, 19), 2)
        pts = []
        for k in range(22):
            a = k / 22 * math.tau
            pts.append(P(-3 + math.cos(a) * 30 * (1 + 0.10 * math.cos(a)), 1 + math.sin(a) * 15.5))
        pygame.draw.polygon(surf, SKIN, pts)
        low = [P(-3 + math.cos(a) * 28, 3 + math.sin(a) * 13.5)
               for a in [k / 12 * math.pi for k in range(13)]]
        pygame.draw.polygon(surf, SKIN_D, low + [P(-24, 0), P(8, 6), P(26, 1)])
        pygame.draw.polygon(surf, INK, pts, 3)
        for kx in (14, 21):
            pygame.draw.circle(surf, SKIN_L, P(kx, -9), 3)
