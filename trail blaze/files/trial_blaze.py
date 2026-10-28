# trial_blaze.py
# TRIAL BLAZE - an HD off-road trials bike game.
#
#   Run it with:   python trial_blaze.py
#
# Menu: PLAY (7 levels), BIKE (buy bikes with gold), ABOUT (how to play).
# Keys: UP/W gas, DOWN/S brake, LEFT/A lean back, RIGHT/D lean forward,
#       R restart from checkpoint, ESC pause/back, F11 fullscreen.

import json
import math
import os
import random

import pygame
from pymunk import Vec2d

import art
from art import W, H, THEMES, draw_text, clamp
from bikes import BIKES, bike_by_id
from levels import LEVEL_BUILDERS, build_level
from physics import World, Bike

FPS = 60
DT = 1.0 / 60.0
COIN_VALUE = 10
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_PATH = os.path.join(BASE_DIR, "save.json")
NUM_LEVELS = len(LEVEL_BUILDERS)


# ---------------------------------------------------------------------------
# saving
# ---------------------------------------------------------------------------

class Save:
    """Gold, owned bikes and level progress, stored in save.json."""

    def __init__(self):
        self.gold = 0
        self.owned = ["rookie"]
        self.bike = "rookie"
        self.levels = {}          # "0" -> {"stars": 3, "best": 21.5}
        self.load()

    def load(self):
        try:
            with open(SAVE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.gold = int(data.get("gold", 0))
            self.owned = list(data.get("owned", ["rookie"])) or ["rookie"]
            self.bike = data.get("bike", "rookie")
            self.levels = dict(data.get("levels", {}))
        except (OSError, ValueError):
            pass
        if self.bike not in self.owned:
            self.bike = "rookie"

    def write(self):
        try:
            with open(SAVE_PATH, "w", encoding="utf-8") as f:
                json.dump({"gold": self.gold, "owned": self.owned, "bike": self.bike,
                           "levels": self.levels}, f, indent=2)
        except OSError:
            pass

    def stars(self, i):
        return self.levels.get(str(i), {}).get("stars", 0)

    def best(self, i):
        return self.levels.get(str(i), {}).get("best")

    def unlocked(self, i):
        return i == 0 or self.stars(i - 1) > 0


# ---------------------------------------------------------------------------
# the game
# ---------------------------------------------------------------------------

class Game:
    def __init__(self):
        pygame.init()
        self.setup_window()
        self.clock = pygame.time.Clock()
        self.save = Save()
        self.t = 0.0
        self.running = True
        self.state = "menu"
        self.hot = []                  # clickable areas: (rect, function)
        self.mouse = (0, 0)
        self.hover_any = False
        self.hand_cursor = False
        self.menu_scenery = art.Scenery("forest", 7)
        self.menu_tile = art.make_dirt_tile(THEMES["forest"])
        self.coin_imgs = art.coin_frames(15, 15)
        self.minis = {}
        self.bike_index = [b["id"] for b in BIKES].index(self.save.bike)
        self.toast_text = ""
        self.toast_t = 0.0
        self.level = None
        self.keys_state = (False, False, 0)

    # ----- window -----
    def setup_window(self):
        pygame.display.set_caption("TRIAL BLAZE")
        try:
            dw, dh = pygame.display.get_desktop_sizes()[0]
        except Exception:
            info = pygame.display.Info()
            dw, dh = info.current_w, info.current_h
        self.screen = None
        if dw >= W and dh >= H + 80:
            try:
                self.screen = pygame.display.set_mode((W, H), pygame.SCALED | pygame.RESIZABLE)
                self.canvas = self.screen
            except pygame.error:
                self.screen = None
        if self.screen is None:
            k = min((dw - 60) / W, (dh - 140) / H, 1.0)
            k = max(k, 0.4)
            self.screen = pygame.display.set_mode((int(W * k), int(H * k)), pygame.RESIZABLE)
            self.canvas = pygame.Surface((W, H))

    def conv(self, pos):
        if self.canvas is self.screen:
            return pos
        sw, sh = self.screen.get_size()
        return (pos[0] * W / sw, pos[1] * H / sh)

    def present(self):
        if self.canvas is not self.screen:
            self.screen = pygame.display.get_surface()
            size = self.screen.get_size()
            if size == (W, H):
                self.screen.blit(self.canvas, (0, 0))
            else:
                pygame.transform.smoothscale(self.canvas, size, self.screen)
        pygame.display.flip()

    # ----- main loop -----
    def run(self):
        acc = 0.0
        while self.running:
            frame_dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            self.t += frame_dt
            self.mouse = self.conv(pygame.mouse.get_pos())
            self.handle_events()
            if self.state == "play":
                acc += frame_dt
                while acc >= DT:
                    self.update_play(DT)
                    acc -= DT
            else:
                acc = 0.0
            if self.toast_t > 0:
                self.toast_t -= frame_dt
            self.draw()
            self.update_cursor()
            self.present()
        pygame.quit()

    def update_cursor(self):
        if self.hover_any != self.hand_cursor:
            self.hand_cursor = self.hover_any
            try:
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND if self.hand_cursor
                                        else pygame.SYSTEM_CURSOR_ARROW)
            except (pygame.error, AttributeError):
                pass

    def handle_events(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                self.running = False
            elif e.type == pygame.KEYDOWN:
                self.on_key(e.key)
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                pos = self.conv(e.pos)
                for rect, fn in reversed(self.hot):
                    if rect.collidepoint(pos):
                        fn()
                        break

    def on_key(self, key):
        if key == pygame.K_F11:
            pygame.display.toggle_fullscreen()
        elif key == pygame.K_ESCAPE:
            if self.state in ("levels", "bike", "about"):
                self.state = "menu"
            elif self.state == "play":
                self.state = "paused"
            elif self.state == "paused":
                self.state = "play"
            elif self.state == "complete":
                self.state = "levels"
        elif key == pygame.K_r and self.state == "play":
            if self.phase == "run":
                self.faults += 1
            if self.phase in ("run", "crash"):
                self.respawn()

    # ----- ui helpers -----
    def button(self, rect, label, fn, color=(255, 140, 20), size=44, enabled=True):
        hover = enabled and rect.collidepoint(self.mouse)
        if hover:
            self.hover_any = True
        art.draw_button(self.canvas, rect, label, hover, enabled, color, size)
        if enabled:
            self.hot.append((rect, fn))

    def back_button(self, target="menu"):
        self.button(pygame.Rect(50, 40, 210, 76), "< BACK", lambda: self.goto(target),
                    color=(90, 80, 190), size=36)

    def goto(self, state):
        self.state = state

    def draw_gold(self):
        rect = pygame.Rect(W - 330, 36, 280, 70)
        art.draw_panel(self.canvas, rect, alpha=220, radius=20)
        art.draw_coin(self.canvas, (rect.x + 44, rect.centery), 22)
        draw_text(self.canvas, f"{self.save.gold}", 44, (255, 226, 110),
                  (rect.right - 24, rect.centery), anchor="midright")

    def toast(self, text):
        self.toast_text = text
        self.toast_t = 2.2

    def draw_toast(self):
        if self.toast_t > 0:
            a = clamp(self.toast_t / 0.5, 0, 1)
            col = (255, int(clamp(226 * a + 30, 0, 255)), int(clamp(110 * a, 0, 255)))
            draw_text(self.canvas, self.toast_text, 54, col, (W // 2, 1030))

    # ----- drawing dispatch -----
    def draw(self):
        self.hot = []
        self.hover_any = False
        c = self.canvas
        if self.state == "menu":
            self.draw_menu()
        elif self.state == "levels":
            self.draw_levels()
        elif self.state == "bike":
            self.draw_bike_shop()
        elif self.state == "about":
            self.draw_about()
        elif self.state in ("play", "paused", "complete"):
            self.draw_play()
            if self.state == "paused":
                self.draw_pause()
            elif self.state == "complete":
                self.draw_complete()
        self.draw_toast()

    # ------------------------------------------------------------------
    # MAIN MENU
    # ------------------------------------------------------------------
    def draw_menu(self):
        c = self.canvas
        th = THEMES["forest"]
        self.menu_scenery.draw(c, self.t * 90, 520, self.t)
        ground = 880
        off = int(self.t * 420) % 512
        for x in range(-off, W, 512):
            for y in range(ground, H, 512):
                c.blit(self.menu_tile, (x, y))
        pygame.draw.rect(c, th["edge"], (0, ground - 2, W, 30))
        pygame.draw.rect(c, th["grass"], (0, ground - 8, W, 18))
        pygame.draw.rect(c, art.shade(th["grass"], 1.28), (0, ground - 8, W, 5))

        spec = bike_by_id(self.save.bike)
        ba = art.bike_art(spec, 2.0)
        spin = self.t * 7.0
        sway = -0.06 + 0.025 * math.sin(self.t * 2.2)
        origin = (1400, ground - 78 * 2.0 - 4 + math.sin(self.t * 9) * 2)
        art.draw_shadow(c, (1400 - 260, ground - 6, 520, 26), 90)
        ba.draw(c, origin, sway, (-76, 48), (76, 48), spin, spin, lean=0.05)

        draw_text(c, "TRIAL", 170, (255, 255, 255), (140, 170), anchor="midleft", shadow=8)
        draw_text(c, "BLAZE", 170, (255, 150, 30), (140, 338), anchor="midleft", shadow=8)
        draw_text(c, "OFF-ROAD TRIALS CHAMPIONSHIP", 32, (235, 235, 250), (146, 456),
                  anchor="midleft", shadow=3)

        self.button(pygame.Rect(140, 520, 540, 104), "PLAY", lambda: self.goto("levels"), size=56)
        self.button(pygame.Rect(140, 648, 540, 96), "BIKE", lambda: self.goto("bike"),
                    color=(60, 150, 255), size=48)
        self.button(pygame.Rect(140, 768, 540, 96), "ABOUT", lambda: self.goto("about"),
                    color=(80, 190, 110), size=48)
        self.button(pygame.Rect(W - 250, H - 90, 200, 62), "QUIT", self.quit_game,
                    color=(190, 60, 60), size=32)
        self.draw_gold()

    def quit_game(self):
        self.running = False

    # ------------------------------------------------------------------
    # LEVEL SELECT
    # ------------------------------------------------------------------
    def mini_for(self, i):
        if i in self.minis:
            return self.minis[i]
        level = build_level(i)
        th = THEMES[level.theme]
        w, h = 366, 170
        s = art.vertical_gradient(w, h, th["sky"][0], th["sky"][1])
        pts_far = [(x, 96 + 18 * math.sin(x / 38.0 + i)) for x in range(0, w + 8, 8)]
        pygame.draw.polygon(s, th["mid"][0], pts_far + [(w, h), (0, h)])
        sx = (w - 16) / level.length
        sy = 0.1
        for chain in level.chains:
            pts = [(8 + x * sx, 132 + (y - level.max_y) * sy) for x, y in chain]
            if len(pts) < 2:
                continue
            pygame.draw.polygon(s, th["dirt"], pts + [(pts[-1][0], h), (pts[0][0], h)])
            pygame.draw.lines(s, th["grass"], False, pts, 4)
        fx = 8 + level.finish_x * sx
        fy = 132 + (level.ground_y(level.finish_x) - level.max_y) * sy
        pygame.draw.line(s, (240, 240, 240), (fx, fy), (fx, fy - 22), 2)
        pygame.draw.polygon(s, (230, 60, 50), [(fx, fy - 22), (fx + 12, fy - 18), (fx, fy - 13)])
        self.minis[i] = s
        return s

    def draw_levels(self):
        c = self.canvas
        self.menu_scenery.draw(c, self.t * 40, 520, self.t)
        shade = pygame.Surface((W, H), pygame.SRCALPHA)
        shade.fill((10, 8, 30, 150))
        c.blit(shade, (0, 0))
        draw_text(c, "SELECT LEVEL", 78, (255, 255, 255), (W // 2, 78))
        self.back_button()
        self.draw_gold()

        cw, ch, gap = 410, 340, 36
        for i in range(NUM_LEVELS):
            row, col = (0, i) if i < 4 else (1, i - 4)
            count = 4 if row == 0 else NUM_LEVELS - 4
            x0 = (W - (count * cw + (count - 1) * gap)) // 2
            rect = pygame.Rect(x0 + col * (cw + gap), 230 + row * (ch + gap), cw, ch)
            unlocked = self.save.unlocked(i)
            hover = unlocked and rect.collidepoint(self.mouse)
            if hover:
                self.hover_any = True
                rect = rect.inflate(14, 14)
            art.draw_panel(c, rect, alpha=240, border=(255, 190, 80) if hover else (150, 120, 255))
            c.blit(self.mini_for(i), (rect.x + (rect.w - 366) // 2, rect.y + 16))
            name = build_level_name(i)
            draw_text(c, f"{i + 1}", 56, (255, 190, 60), (rect.x + 40, rect.y + 214), anchor="midleft")
            draw_text(c, name, 31, (255, 255, 255), (rect.x + 86, rect.y + 214), anchor="midleft", shadow=2)
            stars = self.save.stars(i)
            for s in range(3):
                art.draw_star(c, (rect.x + 52 + s * 52, rect.y + 288), 21, filled=s < stars)
            best = self.save.best(i)
            if best:
                draw_text(c, f"{best:.1f}s", 34, (230, 230, 245), (rect.right - 28, rect.y + 288),
                          anchor="midright", shadow=2)
            if not unlocked:
                dim = pygame.Surface(rect.size, pygame.SRCALPHA)
                pygame.draw.rect(dim, (8, 6, 20, 190), dim.get_rect(), border_radius=22)
                c.blit(dim, rect.topleft)
                art.draw_lock(c, (rect.centerx, rect.y + 92), 84)
                draw_text(c, "FINISH THE PREVIOUS LEVEL", 24, (210, 210, 225),
                          (rect.centerx, rect.y + 152), shadow=2)
            else:
                self.hot.append((rect, lambda i=i: self.start_level(i)))

    # ------------------------------------------------------------------
    # BIKE SHOP
    # ------------------------------------------------------------------
    def draw_bike_shop(self):
        c = self.canvas
        self.menu_scenery.draw(c, 300, 520, self.t)
        shade = pygame.Surface((W, H), pygame.SRCALPHA)
        shade.fill((10, 8, 30, 150))
        c.blit(shade, (0, 0))
        spec = BIKES[self.bike_index]
        owned = spec["id"] in self.save.owned
        selected = spec["id"] == self.save.bike

        draw_text(c, "BIKE SHOP", 78, (255, 255, 255), (W // 2, 78))
        self.back_button()
        self.draw_gold()
        draw_text(c, spec["name"], 70, spec["color"], (1100, 170))
        draw_text(c, spec["blurb"], 30, (225, 225, 240), (1100, 244), shadow=2)

        # stage
        origin = (1100, 610)
        floor_y = origin[1] + 78 * 2.0
        art.draw_shadow(c, (1100 - 380, floor_y - 6, 760, 46), 110)
        pygame.draw.ellipse(c, (60, 56, 90), (1100 - 360, floor_y - 20, 720, 44))
        pygame.draw.ellipse(c, (110, 102, 160), (1100 - 360, floor_y - 24, 720, 40), 4)
        ba = art.bike_art(spec, 2.0)
        spin = self.t * 3
        ba.draw(c, (origin[0], origin[1] + math.sin(self.t * 2) * 4), -0.05, (-76, 48), (76, 48),
                spin, spin, lean=0.04)

        # stats panel
        panel = pygame.Rect(110, 340, 560, 400)
        art.draw_panel(c, panel, alpha=230)
        draw_text(c, "STATS", 40, (255, 255, 255), (panel.centerx, panel.y + 44))
        for r, (label, key) in enumerate((("POWER", "power"), ("SPEED", "speed"),
                                          ("GRIP", "grip"), ("CONTROL", "control"))):
            y = panel.y + 120 + r * 66
            draw_text(c, label, 30, (230, 230, 245), (panel.x + 34, y), anchor="midleft", shadow=2)
            for p in range(10):
                pr = pygame.Rect(panel.x + 200 + p * 34, y - 14, 27, 28)
                filled = p < spec[key]
                pygame.draw.rect(c, spec["color"] if filled else (52, 48, 78), pr, border_radius=6)
                if filled:
                    pygame.draw.rect(c, art.shade(spec["color"], 1.35), (pr.x, pr.y, pr.w, 8), border_radius=6)

        # arrows and dots
        self.button(pygame.Rect(690, 540, 96, 110), "<", self.prev_bike, color=(90, 80, 190), size=64)
        self.button(pygame.Rect(1414, 540, 96, 110), ">", self.next_bike, color=(90, 80, 190), size=64)
        for i in range(len(BIKES)):
            col = BIKES[i]["color"] if i == self.bike_index else (84, 80, 112)
            pygame.draw.circle(c, col, (1100 - 45 + i * 30, 846), 9)

        # buy / select
        btn = pygame.Rect(820, 890, 560, 100)
        if selected:
            self.button(btn, "SELECTED", lambda: None, color=(60, 170, 90), size=50, enabled=False)
        elif owned:
            self.button(btn, "SELECT", lambda: self.select_bike(spec), color=(60, 150, 255), size=54)
        elif self.save.gold >= spec["price"]:
            self.button(btn, f"BUY  {spec['price']}", lambda: self.buy_bike(spec), size=54)
            art.draw_coin(c, (btn.right - 56, btn.centery), 22)
        else:
            self.button(btn, f"NEED {spec['price'] - self.save.gold} MORE GOLD", lambda: None,
                        size=34, enabled=False)
        if not owned:
            art.draw_lock(c, (btn.x - 70, btn.centery - 6), 56)

    def prev_bike(self):
        self.bike_index = (self.bike_index - 1) % len(BIKES)

    def next_bike(self):
        self.bike_index = (self.bike_index + 1) % len(BIKES)

    def select_bike(self, spec):
        self.save.bike = spec["id"]
        self.save.write()
        self.toast("BIKE SELECTED!")

    def buy_bike(self, spec):
        if self.save.gold >= spec["price"] and spec["id"] not in self.save.owned:
            self.save.gold -= spec["price"]
            self.save.owned.append(spec["id"])
            self.save.bike = spec["id"]
            self.save.write()
            self.toast("BIKE UNLOCKED!")

    # ------------------------------------------------------------------
    # ABOUT (how to play)
    # ------------------------------------------------------------------
    def wrap(self, text, size, width):
        f = art.font(size)
        lines, cur = [], ""
        for word in text.split():
            trial = (cur + " " + word).strip()
            if f.size(trial)[0] <= width:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        return lines

    def draw_about(self):
        c = self.canvas
        self.menu_scenery.draw(c, 120, 520, self.t)
        shade = pygame.Surface((W, H), pygame.SRCALPHA)
        shade.fill((10, 8, 30, 170))
        c.blit(shade, (0, 0))
        draw_text(c, "HOW TO PLAY", 78, (255, 255, 255), (W // 2, 78))
        self.back_button()
        k = pygame.key.get_pressed()
        up = k[pygame.K_UP] or k[pygame.K_w]
        down = k[pygame.K_DOWN] or k[pygame.K_s]
        left = k[pygame.K_LEFT] or k[pygame.K_a]
        right = k[pygame.K_RIGHT] or k[pygame.K_d]

        # controls panel
        left_panel = pygame.Rect(60, 150, 1000, 480)
        art.draw_panel(c, left_panel, alpha=232)
        draw_text(c, "CONTROLS  (try the keys!)", 38, (255, 190, 60), (left_panel.x + 40, left_panel.y + 44),
                  anchor="midleft")
        art.draw_keycap(c, pygame.Rect(270, 245, 100, 100), "^", up, 60)
        art.draw_keycap(c, pygame.Rect(150, 360, 100, 100), "<", left, 60)
        art.draw_keycap(c, pygame.Rect(270, 360, 100, 100), "v", down, 60)
        art.draw_keycap(c, pygame.Rect(390, 360, 100, 100), ">", right, 60)
        draw_text(c, "or  W  A  S  D", 28, (190, 190, 210), (320, 500), shadow=0)
        rows = [("UP / W", "GAS", up), ("DOWN / S", "BRAKE / REVERSE", down),
                ("LEFT / A", "LEAN BACK (nose up)", left),
                ("RIGHT / D", "LEAN FORWARD (nose down)", right),
                ("R", "RESTART at checkpoint", k[pygame.K_r]), ("ESC", "PAUSE", k[pygame.K_ESCAPE])]
        for i, (key, text, active) in enumerate(rows):
            y = 240 + i * 58
            col = (255, 220, 90) if active else (235, 235, 248)
            draw_text(c, key, 28, (255, 160, 40) if not active else (255, 240, 120), (560, y), anchor="midleft", shadow=2)
            draw_text(c, text, 28, col, (730, y), anchor="midleft", shadow=2)

        # tips panel
        tips = pygame.Rect(1100, 150, 760, 480)
        art.draw_panel(c, tips, alpha=232)
        draw_text(c, "RIDING TIPS", 38, (255, 190, 60), (tips.x + 40, tips.y + 44), anchor="midleft")
        tip_lines = [
            "Lean BACK to lift the front wheel before a log or a step.",
            "Lean FORWARD in the air so you land on both wheels.",
            "Keep your rider's head off the ground or you crash!",
            "Stay on the gas up hills. Ease off on big bumps.",
            "Be fast for stars. Collect coins for gold.",
        ]
        y = tips.y + 98
        for line in tip_lines:
            pygame.draw.circle(c, (255, 160, 40), (tips.x + 44, y + 13), 8)
            for sub in self.wrap(line, 26, 640):
                draw_text(c, sub, 26, (235, 235, 248), (tips.x + 70, y), anchor="topleft", shadow=2)
                y += 32
            y += 20

        # obstacle guide
        guide = pygame.Rect(60, 660, 1800, 340)
        art.draw_panel(c, guide, alpha=232)
        draw_text(c, "OBSTACLES & ITEMS", 38, (255, 190, 60), (guide.x + 40, guide.y + 44), anchor="midleft")
        items = [("LOG", "Lean back and roll over it"), ("CRATES", "Smash through, stay low"),
                 ("CONTAINER", "Drive up the ramps"), ("GAP", "Jump with speed from a ramp"),
                 ("CHECKPOINT", "You restart here"), ("COINS", "Gold for new bikes")]
        slot = (guide.w - 60) // 6
        for i, (title, desc) in enumerate(items):
            cx = guide.x + 30 + slot * i + slot // 2
            cy = guide.y + 160
            if i == 0:
                img = art.log_sprite(34)
                c.blit(img, img.get_rect(center=(cx, cy)))
            elif i == 1:
                img = art.crate_sprite(56)
                c.blit(img, img.get_rect(center=(cx - 30, cy + 20)))
                c.blit(img, img.get_rect(center=(cx + 30, cy + 20)))
                c.blit(img, img.get_rect(center=(cx, cy - 36)))
            elif i == 2:
                img = art.container_sprite(110, 46, 62, art.CONTAINER_COLORS[0])
                c.blit(img, img.get_rect(center=(cx, cy + 20)))
            elif i == 3:
                pygame.draw.rect(c, (126, 88, 54), (cx - 130, cy, 90, 70))
                pygame.draw.rect(c, (96, 178, 60), (cx - 130, cy, 90, 12))
                pygame.draw.rect(c, (126, 88, 54), (cx + 40, cy + 30, 90, 40))
                pygame.draw.rect(c, (96, 178, 60), (cx + 40, cy + 30, 90, 12))
                pts = [(cx - 40 + t * 8, cy - 12 - math.sin(t / 10 * math.pi) * 50 + t * 4.2) for t in range(11)]
                pygame.draw.lines(c, (255, 200, 60), False, pts, 5)
            elif i == 4:
                art.draw_flag(c, cx - 30, cy + 70, False, self.t, 130)
            else:
                for j in range(3):
                    img = self.coin_imgs[int((math.sin(self.t * 4 + j) * 0.5 + 0.5) * (len(self.coin_imgs) - 1))]
                    c.blit(img, img.get_rect(center=(cx - 50 + j * 50, cy + 10 - (j % 2) * 24)))
            draw_text(c, title, 31, (255, 255, 255), (cx, guide.y + 238), shadow=2)
            for n, sub in enumerate(self.wrap(desc, 24, slot - 20)):
                draw_text(c, sub, 24, (200, 200, 220), (cx, guide.y + 276 + n * 28), shadow=0)

    # ------------------------------------------------------------------
    # PLAYING
    # ------------------------------------------------------------------
    def start_level(self, index):
        self.level_index = index
        self.level = build_level(index)
        theme = self.level.theme
        self.scenery = art.Scenery(theme, seed=index + 1)
        self.terrain = art.TerrainRenderer(self.level, theme)
        self.decos = art.place_decorations(self.level, theme)
        self.world = World(self.level)
        self.spec = bike_by_id(self.save.bike)
        self.bike_art = art.bike_art(self.spec, 1.0)
        self.coins_taken = set()
        self.cp_index = -1
        self.faults = 0
        self.time = 0.0
        self.phase = "countdown"
        self.phase_t = 0.0
        self.grace = 0.0
        self.crash_t = 0.0
        self.lean_vis = 0.0
        self.fade = 0.0
        self.particles = []
        self.toasts = []
        self.result = None
        self.toast_t = 0.0
        self.env = self.make_env_particles(theme)
        self.spawn_bike(self.level.start_x)
        f = self.bike.frame.position
        self.cam = [f.x - W * 0.4, f.y - H * 0.58]
        self.state = "play"

    def make_env_particles(self, theme):
        kind = THEMES[theme]["particles"]
        rnd = random.Random(5)
        if not kind:
            return None
        parts = []
        for _ in range(150):
            parts.append([rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(-1, 1), rnd.uniform(0.5, 1.5),
                          rnd.uniform(2, 5)])
        return (kind, parts)

    def spawn_bike(self, x):
        g = self.level.ground_y(x)
        self.bike = Bike(self.world, self.spec, (x, g - 110), self.level.slope_angle(x))

    def respawn(self):
        self.bike.remove()
        self.world.remove_ragdoll()
        self.world.reset_crates()
        x = self.level.checkpoints[self.cp_index] if self.cp_index >= 0 else self.level.start_x
        self.spawn_bike(x)
        self.phase = "run"
        self.phase_t = 1.0
        self.grace = 0.8
        self.fade = 1.0
        self.lean_vis = 0.0

    def add_toast(self, text, color=(255, 255, 255)):
        self.toasts.append([text, color, 2.0])

    def burst(self, pos, color, n=14, speed=300):
        for _ in range(n):
            a = random.uniform(0, math.tau)
            s = random.uniform(0.3, 1.0) * speed
            self.particles.append([pos[0], pos[1], math.cos(a) * s, math.sin(a) * s - 80,
                                   random.uniform(0.4, 0.9), random.uniform(5, 10), color])

    # ----- update -----
    def update_play(self, dt):
        if self.state != "play":
            return
        k = pygame.key.get_pressed()
        throttle = bool(k[pygame.K_UP] or k[pygame.K_w])
        brake = bool(k[pygame.K_DOWN] or k[pygame.K_s])
        lean = int(bool(k[pygame.K_RIGHT] or k[pygame.K_d])) - int(bool(k[pygame.K_LEFT] or k[pygame.K_a]))
        self.keys_state = (throttle, brake, lean)
        bike = self.bike
        ph = self.phase

        if ph == "countdown":
            throttle = brake = False
            lean = 0
            self.phase_t += dt
            if self.phase_t >= 2.4:
                self.phase, self.phase_t = "run", 0.0
        elif ph == "run":
            self.phase_t += dt
            self.time += dt
            self.grace -= dt
        elif ph == "crash":
            throttle = brake = False
            lean = 0
            self.time += dt
            self.crash_t += dt
        elif ph == "finish":
            throttle = False
            lean = 0
            brake = bike.speed > 40
            self.phase_t += dt

        bike.set_controls(throttle, brake, lean)
        self.world.step(dt, bike)
        self.lean_vis += (lean * 0.2 - self.lean_vis) * min(1.0, dt * 9)
        frame = bike.frame

        if self.phase == "run":
            # coins
            for i, coin in enumerate(self.level.coins):
                if i in self.coins_taken:
                    continue
                if abs(coin["x"] - frame.position.x) < 90 and \
                        (coin["x"] - frame.position.x) ** 2 + (coin["y"] - frame.position.y) ** 2 < 80 ** 2:
                    self.coins_taken.add(i)
                    self.burst((coin["x"], coin["y"]), (255, 214, 60), 12, 260)
            # checkpoints
            for i, cx in enumerate(self.level.checkpoints):
                if i > self.cp_index and frame.position.x > cx:
                    self.cp_index = i
                    self.add_toast("CHECKPOINT!", (110, 240, 130))
            # finish line
            if frame.position.x > self.level.finish_x:
                self.phase, self.phase_t = "finish", 0.0
            # crash
            elif self.grace <= 0 and (bike.crashed() or frame.position.y > self.level.floor_y):
                self.do_crash()
            # dust behind the rear wheel
            if throttle and bike.speed > 60 and bike.wheel_on_ground(bike.rear):
                th = THEMES[self.level.theme]
                p = bike.rear.position + Vec2d(-6, Bike.R - 6)
                self.particles.append([p.x, p.y, -bike.speed * 0.12 + random.uniform(-40, 20),
                                       random.uniform(-120, -30), random.uniform(0.3, 0.6),
                                       random.uniform(6, 13), art.shade(th["dirt"], 1.35)])
        elif self.phase == "crash":
            if self.crash_t > 1.25:
                self.respawn()
        elif self.phase == "finish":
            if self.phase_t > 1.4:
                self.finish_level()

        # camera follows the bike (a little ahead of it)
        target_x = frame.position.x + frame.velocity.x * 0.3 - W * 0.4
        target_y = frame.position.y + frame.velocity.y * 0.08 - H * 0.58
        target_x = clamp(target_x, 0, self.level.length - W)
        self.cam[0] += (target_x - self.cam[0]) * min(1.0, dt * 6)
        self.cam[1] += (target_y - self.cam[1]) * min(1.0, dt * 4)

        # particles
        for p in self.particles:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[3] += 500 * dt
            p[4] -= dt
        self.particles = [p for p in self.particles if p[4] > 0]
        for tmsg in self.toasts:
            tmsg[2] -= dt
        self.toasts = [x for x in self.toasts if x[2] > 0]
        self.fade = max(0.0, self.fade - dt * 2.2)
        if self.env:
            kind, parts = self.env
            for p in parts:
                if kind == "snow":
                    p[0] += (p[2] * 40 - 60) * dt
                    p[1] += (80 + p[3] * 90) * dt
                else:
                    p[0] += p[2] * 30 * dt
                    p[1] -= (60 + p[3] * 80) * dt
                if p[1] > H + 10:
                    p[1] = -10
                if p[1] < -10:
                    p[1] = H + 10
                if p[0] < -10:
                    p[0] = W + 10
                if p[0] > W + 10:
                    p[0] = -10

    def do_crash(self):
        self.faults += 1
        self.phase = "crash"
        self.crash_t = 0.0
        frame = self.bike.frame
        head = self.bike.rider_world(0)
        self.world.add_ragdoll(head, frame.velocity + Vec2d(40, -240))
        self.burst((head.x, head.y), (255, 120, 60), 22, 420)
        self.add_toast("CRASH!", (255, 90, 80))

    def finish_level(self):
        i = self.level_index
        par = self.level.par
        stars = 3 if self.time <= par[0] else 2 if self.time <= par[1] else 1
        coins = len(self.coins_taken)
        gold = 30 + 40 * stars + coins * COIN_VALUE
        prev = self.save.levels.get(str(i), {})
        new_best = (prev.get("best") is None) or self.time < prev["best"]
        self.save.levels[str(i)] = {
            "stars": max(stars, prev.get("stars", 0)),
            "best": round(self.time if new_best else prev["best"], 2),
        }
        self.save.gold += gold
        self.save.write()
        self.result = {"stars": stars, "time": self.time, "faults": self.faults, "coins": coins,
                       "gold": gold, "new_best": new_best, "t0": self.t,
                       "base": 30, "star_gold": 40 * stars, "coin_gold": coins * COIN_VALUE}
        self.state = "complete"

    # ----- drawing the play screen -----
    def draw_play(self):
        c = self.canvas
        level = self.level
        cx, cy = int(self.cam[0]), int(self.cam[1])
        self.scenery.draw(c, cx, cy, self.t)

        for sprite, x, y in self.decos:
            sx = x - cx
            if -300 < sx < W + 100:
                c.blit(sprite, (sx, y - cy))
        self.terrain.draw(c, cx, cy)

        # containers drawn over raised ground
        for n, skin in enumerate(level.skins):
            if skin["x1"] - cx < -50 or skin["x0"] - cx > W + 50:
                continue
            top = level.ground_y(skin["x0"] + 2)
            img = art.skin_sprite(int(skin["x1"] - skin["x0"]), 100,
                                  art.CONTAINER_COLORS[n % len(art.CONTAINER_COLORS)])
            c.blit(img, (skin["x0"] - cx, top - cy))

        self.draw_signs(cx, cy)
        self.draw_obstacles(cx, cy)

        # coins
        for i, coin in enumerate(level.coins):
            if i in self.coins_taken:
                continue
            sx = coin["x"] - cx
            if -40 < sx < W + 40:
                squash = abs(math.cos(self.t * 4 + coin["x"] * 0.01))
                img = self.coin_imgs[int(squash * (len(self.coin_imgs) - 1))]
                bob = math.sin(self.t * 3 + coin["x"] * 0.02) * 5
                c.blit(img, img.get_rect(center=(sx, coin["y"] - cy + bob)))

        # the bike
        bike = self.bike
        frame = bike.frame
        origin = (frame.position.x - cx, frame.position.y - cy)
        self.bike_art.draw(c, origin, frame.angle, bike.rear_local(), bike.front_local(),
                           bike.rear.angle, bike.front.angle, self.lean_vis,
                           show_rider=(self.phase != "crash"))
        if self.phase == "crash" and self.world.ragdoll:
            body = self.world.ragdoll[0]
            img = pygame.transform.rotozoom(self.bike_art.rider, -math.degrees(body.angle), 1.0)
            c.blit(img, img.get_rect(center=(body.position.x - cx, body.position.y - cy)))

        # particles
        for x, y, vx, vy, life, size, color in self.particles:
            r = max(1, int(size * min(1.0, life * 2)))
            pygame.draw.circle(c, color, (int(x - cx), int(y - cy)), r)
        if self.env:
            kind, parts = self.env
            for x, y, _, _, size in parts:
                col = (255, 255, 255) if kind == "snow" else (255, int(120 + size * 20), 40)
                pygame.draw.circle(c, col, (int(x), int(y)), int(size * (0.8 if kind == "snow" else 0.7)))

        self.draw_hud()

    def draw_signs(self, cx, cy):
        c = self.canvas
        level = self.level
        # start sign
        x = level.start_x - 260 - cx
        g = level.ground_y(level.start_x - 260) - cy
        if -300 < x < W + 100:
            pygame.draw.rect(c, (84, 56, 34), (x + 24, g - 150, 14, 150))
            pygame.draw.rect(c, (84, 56, 34), (x + 150, g - 150, 14, 150))
            pygame.draw.rect(c, (236, 232, 220), (x, g - 190, 190, 76), border_radius=8)
            pygame.draw.rect(c, (84, 56, 34), (x, g - 190, 190, 76), 6, border_radius=8)
            draw_text(c, "START", 44, (50, 40, 36), (x + 95, g - 152), shadow=0)
        # checkpoints
        for i, cpx in enumerate(level.checkpoints):
            sx = cpx - cx
            if -100 < sx < W + 100:
                art.draw_flag(c, sx, level.ground_y(cpx) - cy, i <= self.cp_index, self.t)
        # finish gate
        fx = level.finish_x
        if -100 < fx - cx < W + 400:
            g = level.ground_y(fx) - cy
            x0, x1 = fx - cx, fx + 260 - cx
            for pole in (x0, x1):
                for n in range(10):
                    col = (245, 245, 245) if n % 2 == 0 else (30, 30, 36)
                    pygame.draw.rect(c, col, (pole - 9, g - (n + 1) * 32, 18, 32))
            for row in range(2):
                for n in range(13):
                    col = (245, 245, 245) if (n + row) % 2 == 0 else (30, 30, 36)
                    pygame.draw.rect(c, col, (x0 + n * 20, g - 330 + row * 24, 20, 24))
            draw_text(c, "FINISH", 54, (255, 255, 255), ((x0 + x1) // 2, g - 400), shadow=5)

    def draw_obstacles(self, cx, cy):
        c = self.canvas
        for ob in self.level.obstacles:
            sx = ob["x"] - cx
            if sx < -400 or sx > W + 400:
                continue
            if ob["type"] == "log":
                img = art.log_sprite(int(ob["r"]))
                c.blit(img, img.get_rect(center=(sx, ob["y"] - cy)))
            elif ob["type"] == "block":
                if ob["kind"] == "plank":
                    img = art.plank_sprite(int(ob["w"]), int(ob["h"]))
                    c.blit(img, (sx - ob["w"] / 2, ob["y"] - ob["h"] / 2 - cy))
                else:
                    ramp = int(ob["h"] * 1.35)
                    color = art.CONTAINER_COLORS[int(ob["x"]) // 7 % len(art.CONTAINER_COLORS)]
                    img = art.container_sprite(int(ob["w"]), int(ob["h"]), ramp, color)
                    c.blit(img, (sx - ob["w"] / 2 - ramp - 4, ob["y"] - ob["h"] / 2 - 4 - cy))
        img = art.crate_sprite(56)
        for body, _ in self.world.crates:
            if -100 < body.position.x - cx < W + 100:
                rot = pygame.transform.rotozoom(img, -math.degrees(body.angle), 1.0)
                c.blit(rot, rot.get_rect(center=(body.position.x - cx, body.position.y - cy)))

    # ----- HUD -----
    def draw_hud(self):
        c = self.canvas
        level = self.level
        frame = self.bike.frame

        # progress bar at the top, with a red dot
        bx0, bx1, by = 560, W - 560, 52
        span = level.finish_x - level.start_x
        pygame.draw.rect(c, (20, 18, 34), (bx0 - 6, by - 12, bx1 - bx0 + 12, 24), border_radius=12)
        pygame.draw.rect(c, (70, 66, 96), (bx0, by - 6, bx1 - bx0, 12), border_radius=6)
        prog = clamp((frame.position.x - level.start_x) / span, 0, 1)
        pygame.draw.rect(c, (255, 160, 40), (bx0, by - 6, (bx1 - bx0) * prog, 12), border_radius=6)
        for i, cpx in enumerate(level.checkpoints):
            px = bx0 + (bx1 - bx0) * clamp((cpx - level.start_x) / span, 0, 1)
            pygame.draw.line(c, (110, 240, 130) if i <= self.cp_index else (230, 230, 240),
                             (px, by - 14), (px, by + 14), 4)
        pygame.draw.rect(c, (255, 255, 255), (bx1 - 3, by - 20, 4, 40))
        pygame.draw.polygon(c, (255, 255, 255), [(bx1 + 1, by - 20), (bx1 + 20, by - 14), (bx1 + 1, by - 8)])
        pygame.draw.circle(c, (30, 0, 0), (bx0 + (bx1 - bx0) * prog, by), 17)
        pygame.draw.circle(c, (240, 40, 40), (bx0 + (bx1 - bx0) * prog, by), 13)
        draw_text(c, f"LEVEL {level.number}  -  {level.name}", 28, (255, 255, 255), (W // 2, by + 44), shadow=3)

        # coins (top left)
        art.draw_panel(c, pygame.Rect(40, 34, 250, 66), alpha=210, radius=18)
        art.draw_coin(c, (82, 67), 20)
        draw_text(c, f"{len(self.coins_taken)} / {len(level.coins)}", 40, (255, 226, 110), (270, 67),
                  anchor="midright")

        # pause button
        pr = pygame.Rect(W - 110, 30, 76, 76)
        hover = pr.collidepoint(self.mouse)
        if hover:
            self.hover_any = True
        pygame.draw.rect(c, (30, 26, 56) if not hover else (60, 52, 110), pr, border_radius=18)
        pygame.draw.rect(c, (150, 120, 255), pr, 3, border_radius=18)
        pygame.draw.rect(c, (255, 255, 255), (pr.x + 24, pr.y + 20, 10, 36), border_radius=3)
        pygame.draw.rect(c, (255, 255, 255), (pr.x + 44, pr.y + 20, 10, 36), border_radius=3)
        if self.state == "play":
            self.hot.append((pr, lambda: self.goto("paused")))

        # timer (bottom left) and faults
        draw_text(c, f"{self.time:.1f}s", 120, (255, 255, 255), (50, H - 130), anchor="midleft", shadow=7)
        draw_text(c, f"FAULTS  {self.faults}", 36, (255, 190, 90), (56, H - 52), anchor="midleft", shadow=3)

        # speedometer (bottom right)
        art.draw_dial(c, (W - 200, H - 200), 134, self.bike.speed * 0.18)

        # toasts
        for i, (text, color, left) in enumerate(self.toasts[-2:]):
            draw_text(c, text, 76, color, (W // 2, 240 + i * 80), shadow=5)

        # countdown / GO
        if self.phase == "countdown":
            n = 3 - int(self.phase_t / 0.8)
            frac = (self.phase_t % 0.8) / 0.8
            size = int(150 + 70 * (1 - frac))
            draw_text(c, str(max(1, n)), size, (255, 220, 80), (W // 2, 420), shadow=8)
            self.draw_controls_hint()
        elif self.phase == "run" and self.phase_t < 0.8 and self.time < 1.0:
            draw_text(c, "GO!", 190, (110, 255, 130), (W // 2, 420), shadow=9)
        elif self.phase == "crash":
            veil = pygame.Surface((W, H), pygame.SRCALPHA)
            veil.fill((200, 20, 20, int(70 * clamp(self.crash_t * 3, 0, 1))))
            c.blit(veil, (0, 0))
        elif self.phase == "finish":
            draw_text(c, "FINISH!", 180, (255, 235, 90), (W // 2, 420), shadow=9)

        if self.fade > 0:
            veil = pygame.Surface((W, H), pygame.SRCALPHA)
            veil.fill((0, 0, 0, int(255 * self.fade)))
            c.blit(veil, (0, 0))

    def draw_controls_hint(self):
        c = self.canvas
        rect = pygame.Rect(W // 2 - 480, H - 150, 960, 96)
        art.draw_panel(c, rect, alpha=200, radius=20)
        draw_text(c, "UP: GAS     DOWN: BRAKE     LEFT / RIGHT: LEAN     R: RESTART",
                  32, (255, 255, 255), rect.center, shadow=2)

    # ----- pause menu -----
    def draw_pause(self):
        c = self.canvas
        veil = pygame.Surface((W, H), pygame.SRCALPHA)
        veil.fill((8, 6, 24, 190))
        c.blit(veil, (0, 0))
        panel = pygame.Rect(W // 2 - 380, 250, 760, 600)
        art.draw_panel(c, panel)
        draw_text(c, "PAUSED", 90, (255, 255, 255), (W // 2, 340))
        self.button(pygame.Rect(W // 2 - 270, 430, 540, 100), "RESUME", lambda: self.goto("play"),
                    color=(60, 170, 90), size=50)
        self.button(pygame.Rect(W // 2 - 270, 560, 540, 100), "RESTART LEVEL",
                    lambda: self.start_level(self.level_index), size=44)
        self.button(pygame.Rect(W // 2 - 270, 690, 540, 100), "LEVEL SELECT",
                    lambda: self.goto("levels"), color=(90, 80, 190), size=44)

    # ----- level complete -----
    def draw_complete(self):
        c = self.canvas
        r = self.result
        veil = pygame.Surface((W, H), pygame.SRCALPHA)
        veil.fill((8, 6, 24, 190))
        c.blit(veil, (0, 0))
        panel = pygame.Rect(W // 2 - 560, 110, 1120, 860)
        art.draw_panel(c, panel)
        age = self.t - r["t0"]
        draw_text(c, "LEVEL COMPLETE!", 92, (255, 220, 80), (W // 2, 190))
        draw_text(c, f"{self.level.name}", 40, (255, 255, 255), (W // 2, 262), shadow=3)

        for s in range(3):
            show = age > 0.3 + s * 0.45
            if show and s < r["stars"]:
                grow = clamp((age - 0.3 - s * 0.45) / 0.35, 0, 1)
                size = 78 * (1 + (1 - grow) * 1.2)
                art.draw_star(c, (W // 2 - 150 + s * 150, 380), size, True, (1 - grow) * 0.8)
            else:
                art.draw_star(c, (W // 2 - 150 + s * 150, 380), 78, False)

        rows = [("TIME", f"{r['time']:.1f}s" + ("   NEW BEST!" if r["new_best"] else "")),
                ("FAULTS", str(r["faults"])), ("COINS", f"{r['coins']} / {len(self.level.coins)}")]
        for i, (label, value) in enumerate(rows):
            y = 520 + i * 54
            draw_text(c, label, 36, (200, 200, 225), (W // 2 - 300, y), anchor="midleft", shadow=2)
            draw_text(c, value, 40, (255, 255, 255), (W // 2 + 300, y), anchor="midright", shadow=2)
        pygame.draw.line(c, (110, 100, 170), (W // 2 - 320, 686), (W // 2 + 320, 686), 3)
        gold_rows = [("LEVEL REWARD", r["base"]), ("STARS", r["star_gold"]), ("COINS", r["coin_gold"])]
        for i, (label, value) in enumerate(gold_rows):
            y = 716 + i * 40
            draw_text(c, label, 28, (190, 190, 215), (W // 2 - 300, y), anchor="midleft", shadow=0)
            draw_text(c, f"+{value}", 30, (255, 226, 110), (W // 2 + 300, y), anchor="midright", shadow=0)
        art.draw_coin(c, (W // 2 - 235, 856), 24)
        draw_text(c, f"+{r['gold']} GOLD", 56, (255, 226, 110), (W // 2 + 30, 856))

        by = 890
        has_next = self.level_index + 1 < NUM_LEVELS
        self.button(pygame.Rect(W // 2 - 520, by, 330, 80), "RETRY",
                    lambda: self.start_level(self.level_index), color=(90, 80, 190), size=40)
        self.button(pygame.Rect(W // 2 - 165, by, 330, 80), "LEVELS", lambda: self.goto("levels"),
                    color=(60, 150, 255), size=40)
        if has_next:
            self.button(pygame.Rect(W // 2 + 190, by, 330, 80), "NEXT",
                        lambda: self.start_level(self.level_index + 1), size=40)


def build_level_name(i):
    from levels import LEVEL_NAMES
    return LEVEL_NAMES[i]


def main():
    Game().run()


if __name__ == "__main__":
    main()
