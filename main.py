"""Reintegrate - you are a hand, crossing a sleeping city to find a piano.

Run:  python main.py            (camera hand-control on if a webcam is available)
      python main.py --no-camera
"""
import argparse
import math
import os
import random
import sys

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame  # noqa: E402

from game import fx, world  # noqa: E402
from game.fx import W, H, BAR, INK  # noqa: E402
from game.hand import Hand  # noqa: E402
from game.tracker import HandTracker, CONNECTIONS, DEAD, JUMP_ON  # noqa: E402

DORIAN = [0, 2, 3, 5, 7, 9, 10]
CREAM = (238, 228, 208)


class Inp:
    def __init__(self, move=0.0, jump_held=False, crouch=False, jump_pressed=False):
        self.move, self.jump_held, self.crouch, self.jump_pressed = move, jump_held, crouch, jump_pressed


class Game:
    def __init__(self, camera=True, dev=False):
        pygame.mixer.pre_init(22050, -16, 2, 512)
        pygame.init()
        try:
            self.screen = pygame.display.set_mode((W, H), pygame.SCALED | pygame.RESIZABLE)
        except pygame.error:
            self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption("Reintegrate")
        pygame.mouse.set_visible(False)
        self.clock = pygame.time.Clock()
        self.dev = dev
        self.audio = fx.Audio()
        self.parts = fx.Particles()
        self.grain = fx.make_grain()
        self.vignette = fx.make_vignette()
        self.tracker = HandTracker()
        self.cam_on = camera
        if camera:
            self.tracker.start()
        self.total = world.total_echoes()
        self.rain = [[random.uniform(0, W + 300), random.uniform(0, H)] for _ in range(120)]
        self.streaks = [[random.uniform(0, W), random.uniform(BAR, H - BAR), random.uniform(40, 140)]
                        for _ in range(46)]
        self.running = True
        self.paused = False
        self.prev_jump = False
        self.reset()

    def reset(self):
        self.t = 0.0
        self.state = "title"
        self.echoes = 0
        self.sub, self.sub_t = "", 9.0
        self.fade, self.fade_to, self.fade_time, self.after = 1.0, 0.0, 1.2, None
        self.end_t = 0.0
        self.load(0)

    # ------------------------------------------------------------ flow
    def load(self, i):
        self.ci = i
        self.level = world.build(i)
        self.theme = world.THEMES[self.level.theme]
        self.sky, self.back, self.front = world.build_bg(self.level.theme, 5 + i)
        self.cp = self.level.spawn
        self.hand = Hand(*self.cp)
        self.dead = False
        self.card = 0.0
        self.last_key = None
        self.gust = "calm"
        self.parts.clear()
        self.audio.ambience(self.level.theme)
        self.snap_camera()

    def snap_camera(self):
        self.camx = fx.clamp(self.hand.cx - W * 0.42, 0, self.level.width - W)
        self.camy = min(40.0, self.hand.bottom - 560)

    def fade_out(self, seconds, then):
        self.fade_to, self.fade_time, self.after = 1.0, seconds, then

    def checkpoint(self, x, fy):
        self.cp = (x, fy)
        self.audio.note(62, 0.5)
        self.audio.note(69, 0.35)

    def collect(self, echo):
        self.echoes += 1
        self.sub, self.sub_t = echo.text, 0.0
        i = min(self.echoes - 1, len(fx.SCALE) - 3)
        self.audio.note(fx.SCALE[i], 0.9)
        self.audio.note(fx.SCALE[i + 2], 0.5)
        for _ in range(14):
            a = random.uniform(0, math.tau)
            self.parts.add(echo.x, echo.y, math.cos(a) * 90, math.sin(a) * 90, 0.7, 4, (255, 224, 160))

    def kill(self):
        if self.dead or self.state != "play":
            return
        self.dead = True
        self.audio.play("caught")
        for _ in range(18):
            a = random.uniform(0, math.tau)
            self.parts.add(self.hand.cx, self.hand.y + 20, math.cos(a) * 160, math.sin(a) * 160 - 60,
                           0.5, 5, (230, 200, 180), grav=500)
        self.fade_out(0.4, self.respawn)

    def respawn(self):
        self.hand = Hand(*self.cp)
        self.dead = False
        self.fade_to, self.fade_time = 0.0, 0.5
        self.snap_camera()

    def next_chapter(self):
        if self.dead:
            return
        self.dead = True

        def go():
            self.load(self.ci + 1)
            self.fade_to, self.fade_time = 0.0, 1.2
        self.fade_out(0.9, go)

    def toggle_camera(self):
        self.cam_on = not self.cam_on
        if self.cam_on:
            self.tracker.start()
        else:
            self.tracker.stop()

    # ------------------------------------------------------------ input
    def read_input(self):
        k = pygame.key.get_pressed()
        move = float((k[pygame.K_d] or k[pygame.K_RIGHT]) - (k[pygame.K_a] or k[pygame.K_LEFT]))
        jump = bool(k[pygame.K_SPACE] or k[pygame.K_w] or k[pygame.K_UP])
        crouch = bool(k[pygame.K_s] or k[pygame.K_DOWN] or k[pygame.K_LCTRL])
        tr = self.tracker
        if self.cam_on and tr.present:
            if move == 0:
                move = tr.move
            jump = jump or tr.jump
            crouch = crouch or tr.fist
        return Inp(move, jump, crouch)

    def events(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                self.running = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    if self.state == "play":
                        self.paused = not self.paused
                    else:
                        self.running = False
                elif e.key == pygame.K_q and self.paused:
                    self.running = False
                elif e.key == pygame.K_F11:
                    pygame.display.toggle_fullscreen()
                elif e.key == pygame.K_c:
                    self.toggle_camera()
                elif e.key == pygame.K_RETURN and self.state == "ending" and self.end_t > 4:
                    self.reset()
                elif e.key == pygame.K_n and self.dev and self.state == "play" and self.ci < 3:
                    self.next_chapter()

    # ------------------------------------------------------------ update
    def update(self, dt, inp):
        inp.jump_pressed = inp.jump_held and not self.prev_jump
        self.prev_jump = inp.jump_held
        if self.paused:
            return
        self.t += dt
        if self.fade != self.fade_to:
            step = dt / self.fade_time
            self.fade = min(self.fade_to, self.fade + step) if self.fade < self.fade_to \
                else max(self.fade_to, self.fade - step)
            if self.fade == self.fade_to and self.after:
                f, self.after = self.after, None
                f()

        lv = self.level
        if self.state == "title":
            if inp.jump_pressed or pygame.key.get_pressed()[pygame.K_RETURN]:
                self.state, self.card = "play", 0.0
            inp = Inp()
        elif self.state == "ending":
            self.end_t += dt
            inp = Inp()

        u = self.t % world.GUST_CYCLE
        gust = "calm" if (not lv.wind or u < 3.6) else "warn" if u < 4.3 else "gust"
        if gust == "warn" and self.gust == "calm":
            self.audio.play("gust")
        self.gust = gust

        for q in lv.solids:
            if q.hit_t < 5:
                q.hit_t += dt
        for e in lv.ents:
            e.update(dt, self)
        h = self.hand
        if not self.dead:
            h.update(dt, inp, lv, gust == "gust")
            if h.jumped:
                self.audio.play("jump")
            if h.landed:
                self.audio.play("land", 0.7)
                for s in (-1, 1):
                    self.parts.add(h.cx + s * 20, h.bottom - 3, s * 70, -30, 0.35, 4, (200, 200, 200), alpha=70)
            if h.bounced:
                self.audio.play("bounce")
            if h.stepped and abs(h.vx) > 40:
                self.audio.play("step", random.uniform(0.5, 1.0))
            g = h.ground
            if g is not None and g.kind == "key":
                if g is not self.last_key:
                    self.last_key = g
                    g.hit_t = 0.0
                    self.audio.note(50 + 12 * (g.key // 7) + DORIAN[g.key % 7], 0.9)
            elif not h.on_ground:
                self.last_key = None
            if self.state == "play":
                self.card += dt
                if h.y > 900:
                    self.kill()
                elif h.cx > lv.exit_x:
                    self.next_chapter()
                elif h.on_ground and h.cx > getattr(lv, "end_x", 1e9):
                    self.state, self.end_t = "ending", 0.0
                    for i, m in enumerate((62, 65, 69, 74)):
                        self.audio.note(m, 0.6 - i * 0.08)

        self.parts.update(dt)
        self.sub_t += dt
        self.audio.tick(dt)

        tx = fx.clamp(h.cx - W * 0.42 + h.facing * 70, 0, lv.width - W)
        ty = min(40.0, h.bottom - 560)
        self.camx += (tx - self.camx) * min(1.0, dt * 4.5)
        self.camy += (ty - self.camy) * min(1.0, dt * 5)

        if lv.rain:
            for d in self.rain:
                d[0] -= 260 * dt
                d[1] += 1500 * dt
                if d[1] > H:
                    d[0], d[1] = random.uniform(0, W + 300), random.uniform(-80, 0)
        if gust != "calm":
            speed = 1700 if gust == "gust" else 500
            for s in self.streaks:
                s[0] -= speed * dt
                if s[0] < -160:
                    s[0], s[1] = W + random.uniform(0, 300), random.uniform(BAR, H - BAR)

    # ------------------------------------------------------------ draw
    def draw(self):
        s = self.screen
        lv = self.level
        cx, cy = int(self.camx), int(self.camy)
        s.blit(self.sky, (0, 0))
        for layer, f in self.back:
            x = -(cx * f) % world.LW - world.LW
            y = -cy * f * 0.6
            while x < W:
                s.blit(layer, (x, y))
                x += world.LW
        hint_col = fx.mix(self.theme["top"], (255, 255, 255), 0.25)
        for hx, hy, txt in lv.hints:
            if self.state == "play" and -400 < hx - cx < W + 400:
                fx.text(s, txt, 24, hint_col, (hx - cx, hy - cy), alpha=150, italic=True)
        for e in lv.ents:
            if e.layer == 0:
                e.draw(s, cx, cy, self)
        for q in lv.solids:
            world.draw_solid(s, q, cx, cy, self.theme, self.t)
        for e in lv.ents:
            if e.layer == 1:
                e.draw(s, cx, cy, self)
        if not self.dead or self.after is None:
            self.hand.draw(s, cx, cy)
        self.parts.draw(s, cx, cy)
        for layer, f in self.front:
            x = -(cx * f) % world.LW - world.LW
            while x < W:
                s.blit(layer, (x, 0))
                x += world.LW
        if lv.rain:
            for x, y in self.rain:
                pygame.draw.line(s, (112, 132, 158), (x, y), (x - 5, y + 28), 1)
        if self.gust != "calm":
            col = (210, 200, 214) if self.gust == "gust" else (150, 130, 150)
            for x, y, ln in self.streaks:
                pygame.draw.line(s, col, (x, y), (x + ln, y), 2 if self.gust == "gust" else 1)

        if self.grain:
            s.blit(self.grain[int(self.t * 14) % len(self.grain)], (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        s.blit(self.vignette, (0, 0))
        pygame.draw.rect(s, (0, 0, 0), (0, 0, W, BAR))
        pygame.draw.rect(s, (0, 0, 0), (0, H - BAR, W, BAR))

        if self.state == "play":
            self.draw_hud(s)
        if self.fade > 0:
            veil = pygame.Surface((W, H))
            veil.set_alpha(int(255 * self.fade))
            s.blit(veil, (0, 0))
        if self.state == "title":
            self.draw_title(s)
        elif self.state == "ending":
            self.draw_ending(s)
        if self.cam_on:
            self.draw_camera(s)
        if self.paused:
            veil = pygame.Surface((W, H))
            veil.set_alpha(150)
            s.blit(veil, (0, 0))
            fx.text(s, "paused", 54, CREAM, (W / 2, H / 2 - 30), italic=True)
            fx.text(s, "ESC resume     Q quit     C camera on/off     F11 fullscreen", 22, CREAM, (W / 2, H / 2 + 34), alpha=190)

    def draw_hud(self, s):
        lv = self.level
        c = self.card
        if c < 6:
            a = 255 * fx.clamp(min(c - 0.6, 5.6 - c), 0, 1)
            fx.text(s, lv.numeral + ".  " + lv.name, 56, CREAM, (96, 150), center=False, alpha=a)
            fx.text(s, lv.sub, 26, CREAM, (100, 218), center=False, alpha=a * 0.8, italic=True)
        if self.sub_t < 6:
            a = 255 * fx.clamp(min(self.sub_t / 0.5, (6 - self.sub_t) / 0.8), 0, 1)
            fx.text(s, self.sub, 30, INK, (W / 2 + 2, H - BAR - 40 + 2), alpha=a * 0.8, italic=True)
            fx.text(s, self.sub, 30, (250, 232, 196), (W / 2, H - BAR - 40), alpha=a, italic=True)
        fx.text(s, "echoes  %d / %d" % (self.echoes, self.total), 18, CREAM, (24, H - BAR + 13), center=False, alpha=150)
        if self.gust == "warn" and int(self.t * 6) % 2:
            fx.text(s, "wind", 22, CREAM, (W / 2, BAR + 24), alpha=170, italic=True)

    def draw_title(self, s):
        veil = pygame.Surface((W, H))
        veil.set_alpha(120)
        s.blit(veil, (0, 0))
        fx.text(s, "REINTEGRATE", 84, CREAM, (W / 2, 200), spacing=16)
        fx.text(s, "You are a hand. Somewhere across the city, a piano has gone quiet.", 26, CREAM,
                (W / 2, 284), alpha=210, italic=True)
        rows = [("move", "A  D   /   arrow keys", "hand left or right of centre"),
                ("jump", "SPACE", "raise your hand"),
                ("crouch, hold on, keep still", "S", "close your fist")]
        fx.text(s, "keyboard", 18, fx.WARM, (W / 2 - 40, 356), alpha=200)
        fx.text(s, "camera", 18, fx.WARM, (W / 2 + 250, 356), alpha=200)
        for i, (what, kb, cam) in enumerate(rows):
            y = 392 + i * 34
            fx.text(s, what, 22, CREAM, (W / 2 - 400, y - 13), center=False, alpha=170, italic=True)
            fx.text(s, kb, 22, CREAM, (W / 2 - 40, y))
            fx.text(s, cam, 22, CREAM, (W / 2 + 250, y))
        a = 150 + 100 * math.sin(self.t * 3)
        prompt = "press ENTER" + ("  -  or raise your open hand" if self.cam_on and self.tracker.status == "ready" else "")
        fx.text(s, prompt, 28, CREAM, (W / 2, 548), alpha=a)
        fx.text(s, "C camera on/off     F11 fullscreen     ESC quit", 18, CREAM, (W / 2, 600), alpha=130)

    def draw_ending(self, s):
        t = self.end_t
        veil = pygame.Surface((W, H))
        veil.fill((250, 236, 208))
        veil.set_alpha(int(240 * fx.clamp((t - 1.5) / 4, 0, 1)))
        s.blit(veil, (0, 0))

        def line(txt, size, y, at, **kw):
            fx.text(s, txt, size, INK, (W / 2, y), alpha=255 * fx.clamp((t - at) / 1.5, 0, 1), **kw)
        line("The piano is no longer quiet.", 40, 250, 4.5, italic=True)
        line("REINTEGRATE", 60, 340, 6.5, spacing=14)
        line("echoes remembered   %d / %d" % (self.echoes, self.total), 24, 420, 8)
        line("ENTER to begin again     ESC to leave", 20, 500, 9.5)

    def draw_camera(self, s):
        tr = self.tracker
        box = pygame.Rect(W - 188, BAR + 12, 172, 129)
        panel = pygame.Surface(box.size, pygame.SRCALPHA)
        panel.fill((8, 10, 16, 150))
        if tr.status == "ready":
            for gx in (0.5 - DEAD, 0.5 + DEAD):
                pygame.draw.line(panel, (120, 130, 150, 120), (gx * box.w, 0), (gx * box.w, box.h), 1)
            pygame.draw.line(panel, (246, 196, 120, 140), (0, JUMP_ON * box.h), (box.w, JUMP_ON * box.h), 1)
            if tr.present and len(tr.points) == 21:
                pts = [(p[0] * box.w, p[1] * box.h) for p in tr.points]
                col = (255, 150, 120) if tr.fist else (246, 214, 170)
                for a, b in CONNECTIONS:
                    pygame.draw.line(panel, col, pts[a], pts[b], 2)
        s.blit(panel, box)
        pygame.draw.rect(s, (90, 100, 120), box, 1)
        label = tr.message
        if tr.status == "ready":
            label = ("fist" if tr.fist else "jump" if tr.jump else "tracking") if tr.present else "show your hand"
        fx.text(s, label, 16, CREAM, (box.centerx, box.bottom + 12), alpha=190)

    # ------------------------------------------------------------ loop
    def frame(self, dt, inp=None):
        self.events()
        self.update(dt, inp if inp is not None else self.read_input())
        self.draw()
        pygame.display.flip()

    def run(self):
        while self.running:
            self.frame(min(self.clock.tick(60) / 1000.0, 1 / 30))
        self.tracker.stop()
        pygame.quit()


def main():
    ap = argparse.ArgumentParser(description="Reintegrate")
    ap.add_argument("--no-camera", action="store_true", help="keyboard only")
    ap.add_argument("--dev", action="store_true", help="N skips to the next chapter")
    args = ap.parse_args()
    Game(camera=not args.no_camera, dev=args.dev).run()


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    main()
