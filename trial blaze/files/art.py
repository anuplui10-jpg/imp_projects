# art.py
# All the drawing code that makes the game look good: backgrounds, ground,
# trees, bikes, buttons and icons. Everything is pre-drawn at a larger size
# and shrunk (super-sampling), which gives smooth, sharp "HD" edges.

import math
import random

import pygame

W, H = 1920, 1080

# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_color(c1, c2, t):
    return tuple(int(lerp(c1[i], c2[i], t)) for i in range(3))


def shade(color, k):
    """Make a color lighter (k > 1) or darker (k < 1)."""
    return tuple(int(clamp(c * k, 0, 255)) for c in color)


def vertical_gradient(w, h, top, bottom):
    surf = pygame.Surface((w, h))
    for y in range(h):
        pygame.draw.line(surf, lerp_color(top, bottom, y / max(1, h - 1)), (0, y), (w, y))
    return surf


_FONTS = {}


def font(size, bold=True):
    key = (size, bold)
    if key not in _FONTS:
        _FONTS[key] = pygame.font.SysFont("arialblack,impact,arial,dejavusans", size, bold=bold)
    return _FONTS[key]


def draw_text(surf, text, size, color, pos, anchor="center", shadow=3, bold=True,
              shadow_color=(0, 0, 0)):
    f = font(size, bold)
    img = f.render(text, True, color)
    rect = img.get_rect()
    setattr(rect, anchor, pos)
    if shadow:
        sh = f.render(text, True, shadow_color)
        sh.set_alpha(150)
        surf.blit(sh, rect.move(shadow, shadow))
    surf.blit(img, rect)
    return rect


def draw_shadow(surf, rect, alpha=80):
    """A soft dark ellipse (pygame.draw ignores alpha on normal surfaces)."""
    rect = pygame.Rect(rect)
    s = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.ellipse(s, (0, 0, 0, alpha), s.get_rect())
    surf.blit(s, rect.topleft)


def draw_rect_alpha(surf, color, rect, radius=0):
    rect = pygame.Rect(rect)
    s = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(s, color, s.get_rect(), border_radius=radius)
    surf.blit(s, rect.topleft)


def supersample(w, h, factor=3):
    """A big transparent surface to draw on; shrink it later with shrink()."""
    return pygame.Surface((int(w * factor), int(h * factor)), pygame.SRCALPHA)


def shrink(big, factor, scale=1.0):
    w = max(1, int(big.get_width() / factor * scale))
    h = max(1, int(big.get_height() / factor * scale))
    return pygame.transform.smoothscale(big, (w, h))


# ---------------------------------------------------------------------------
# themes
# ---------------------------------------------------------------------------

THEMES = {
    "forest": dict(
        sky=((90, 160, 235), (210, 235, 252)), far=((125, 165, 190), (165, 200, 215)),
        mid=((75, 135, 115), (100, 155, 130)), near=((38, 98, 70), (52, 120, 84)),
        dirt=(126, 88, 54), grass=(96, 178, 60), edge=(62, 40, 26),
        deco=["pine", "round", "bush", "round"], sun=((1480, 190), (255, 246, 205), 85),
        particles=None, stars=False, spiky=True),
    "rocky": dict(
        sky=((135, 160, 190), (222, 228, 236)), far=((140, 150, 168), (180, 188, 200)),
        mid=((112, 120, 134), (140, 148, 160)), near=((86, 94, 104), (108, 116, 124)),
        dirt=(112, 102, 94), grass=(120, 150, 86), edge=(66, 58, 52),
        deco=["rock", "dead", "pine", "rock"], sun=((400, 200), (250, 250, 245), 70),
        particles=None, stars=False, spiky=False),
    "dusk": dict(
        sky=((250, 120, 80), (255, 214, 150)), far=((190, 105, 120), (225, 150, 130)),
        mid=((140, 78, 100), (175, 105, 112)), near=((92, 58, 78), (120, 76, 88)),
        dirt=(104, 80, 70), grass=(150, 156, 72), edge=(60, 44, 40),
        deco=["rock", "bush", "dead", "rock"], sun=((1350, 520), (255, 232, 160), 130),
        particles=None, stars=False, spiky=False),
    "desert": dict(
        sky=((84, 164, 240), (248, 226, 176)), far=((232, 190, 128), (240, 208, 154)),
        mid=((214, 160, 96), (228, 182, 116)), near=((190, 132, 74), (210, 156, 92)),
        dirt=(205, 152, 92), grass=(232, 192, 108), edge=(150, 100, 56),
        deco=["cactus", "rock", "cactus", "dead"], sun=((1500, 170), (255, 250, 210), 95),
        particles=None, stars=False, spiky=False),
    "snow": dict(
        sky=((140, 186, 232), (238, 247, 255)), far=((196, 214, 236), (222, 234, 247)),
        mid=((164, 186, 214), (196, 212, 232)), near=((120, 150, 186), (156, 180, 208)),
        dirt=(128, 112, 104), grass=(242, 248, 252), edge=(150, 172, 198),
        deco=["snowpine", "snowpine", "rock", "snowpine"], sun=((420, 180), (255, 255, 240), 70),
        particles="snow", stars=False, spiky=True),
    "night": dict(
        sky=((8, 12, 40), (44, 56, 108)), far=((30, 40, 84), (48, 60, 108)),
        mid=((22, 30, 66), (36, 46, 88)), near=((14, 20, 46), (24, 32, 62)),
        dirt=(64, 58, 82), grass=(52, 118, 96), edge=(30, 28, 44),
        deco=["dead", "rock", "dead", "rock"], sun=((1450, 190), (235, 240, 255), 70),
        particles=None, stars=True, spiky=False),
    "volcano": dict(
        sky=((50, 10, 12), (230, 100, 34)), far=((92, 28, 24), (150, 52, 30)),
        mid=((62, 20, 20), (104, 36, 26)), near=((36, 14, 14), (62, 24, 18)),
        dirt=(72, 46, 42), grass=(196, 70, 28), edge=(40, 22, 20),
        deco=["dead", "rock", "dead", "rock"], sun=((1380, 560), (255, 190, 90), 150),
        particles="ember", stars=False, spiky=False),
}


# ---------------------------------------------------------------------------
# scenery: sky, mountains, trees (parallax = layers move at different speeds)
# ---------------------------------------------------------------------------

TILE_W = 2048


def make_ridge(top_color, bottom_color, base, amp, seed, spiky=False, height=900):
    rnd = random.Random(seed)
    comps = [(k, rnd.random() * math.tau, amp / (k ** 0.75)) for k in (1, 2, 3, 5, 8)]
    pts = []
    for x in range(0, TILE_W + 1, 8):
        y = base
        for k, ph, a in comps:
            y += a * math.sin(math.tau * k * x / TILE_W + ph)
        if spiky:
            y -= 38 * abs(math.sin(math.tau * 46 * x / TILE_W)) ** 0.7
            y -= 20 * abs(math.sin(math.tau * 83 * x / TILE_W + 1.3)) ** 0.7
        pts.append((x, y))
    mask = pygame.Surface((TILE_W, height), pygame.SRCALPHA)
    pygame.draw.polygon(mask, (255, 255, 255, 255), pts + [(TILE_W, height), (0, height)])
    grad = vertical_gradient(TILE_W, height, top_color, bottom_color).convert_alpha()
    grad.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return grad


class Scenery:
    def __init__(self, theme_name, seed=1):
        t = THEMES[theme_name]
        self.theme = t
        rnd = random.Random(seed)
        sky = vertical_gradient(W, H, t["sky"][0], t["sky"][1])
        # sun or moon with a soft glow
        (sx, sy), col, radius = t["sun"]
        glow = pygame.Surface((radius * 6, radius * 6), pygame.SRCALPHA)
        for i in range(24, 0, -1):
            a = int(5 + (24 - i) * 1.2)
            pygame.draw.circle(glow, (*col, a), (radius * 3, radius * 3), int(radius * (1 + i / 12)))
        sky.blit(glow, (sx - radius * 3, sy - radius * 3))
        pygame.draw.circle(sky, col, (sx, sy), radius)
        if t["stars"]:
            for _ in range(160):
                x, y = rnd.randint(0, W), rnd.randint(0, int(H * 0.7))
                v = rnd.randint(150, 255)
                pygame.draw.circle(sky, (v, v, 255), (x, y), rnd.choice((1, 1, 2)))
        self.sky = sky
        self.layers = [
            (make_ridge(*t["far"], 330, 120, seed + 1), 0.05, 0.04, 90),
            (make_ridge(*t["mid"], 330, 95, seed + 2), 0.12, 0.08, 320),
            (make_ridge(*t["near"], 330, 60, seed + 3, spiky=t["spiky"]), 0.26, 0.15, 520),
        ]
        self.clouds = []
        if not t["stars"]:
            for i in range(7):
                self.clouds.append((self.make_cloud(rnd), rnd.randint(0, TILE_W),
                                    rnd.randint(60, 380), rnd.uniform(6, 18)))

    @staticmethod
    def make_cloud(rnd):
        w, h = 360, 130
        big = supersample(w, h, 2)
        for _ in range(7):
            cx = rnd.randint(64, w - 64) * 2
            cy = rnd.randint(60, 70) * 2
            r = rnd.randint(30, 52) * 2
            pygame.draw.circle(big, (255, 255, 255, 120), (cx, cy), r)
        return shrink(big, 2)

    def draw(self, surf, cam_x, cam_y, t):
        surf.blit(self.sky, (0, 0))
        for img, x, y, speed in self.clouds:
            px = (x + t * speed - cam_x * 0.03) % (TILE_W + 400) - 300
            surf.blit(img, (px, y - cam_y * 0.02))
        for layer, fx, fy, y0 in self.layers:
            off = int(cam_x * fx) % TILE_W
            y = int(y0 - (cam_y - 500) * fy)
            surf.blit(layer, (-off, y))
            surf.blit(layer, (TILE_W - off, y))
            # fill underneath so there is no gap when the camera goes up
            bottom = layer.get_at((0, layer.get_height() - 1))[:3]
            pygame.draw.rect(surf, bottom, (0, y + layer.get_height() - 2, W, H))


# ---------------------------------------------------------------------------
# trees, rocks, cactus ... (decorations behind the track)
# ---------------------------------------------------------------------------

def make_deco(kind, theme, rnd):
    f = 3
    if kind in ("pine", "snowpine"):
        w, h = 120, 260
        big = supersample(w, h, f)
        snow = kind == "snowpine"
        trunk = (84, 56, 36)
        pygame.draw.rect(big, trunk, (int(55 * f), int(215 * f), int(10 * f), int(45 * f)))
        for i in range(4):
            top = 20 + i * 48
            half = 28 + i * 11
            base = top + 70
            col = (44, 108, 66) if not snow else (60, 100, 90)
            col = shade(col, 0.85 + 0.1 * i)
            pts = [(60 * f, top * f), ((60 - half) * f, base * f), ((60 + half) * f, base * f)]
            pygame.draw.polygon(big, col, pts)
            hl = [(60 * f, top * f), ((60 - half * 0.1) * f, (top + 20) * f),
                  ((60 - half) * f, base * f)]
            pygame.draw.polygon(big, shade(col, 1.25), hl)
            if snow:
                cap = [(60 * f, top * f), ((60 - half * 0.45) * f, (top + 32) * f),
                       ((60 + half * 0.45) * f, (top + 32) * f)]
                pygame.draw.polygon(big, (245, 250, 255), cap)
        return shrink(big, f), (60, 258)
    if kind == "round":
        w, h = 190, 250
        big = supersample(w, h, f)
        pygame.draw.rect(big, (88, 58, 36), (int(88 * f), int(150 * f), int(16 * f), int(100 * f)))
        col = (58, 140, 70)
        for cx, cy, r in ((95, 90, 62), (58, 110, 44), (132, 112, 46), (95, 60, 40)):
            pygame.draw.circle(big, shade(col, 0.88), (cx * f, cy * f), r * f)
        for cx, cy, r in ((85, 80, 46), (112, 100, 34), (62, 104, 28)):
            pygame.draw.circle(big, shade(col, 1.12), (cx * f, cy * f), r * f)
        return shrink(big, f), (95, 248)
    if kind == "bush":
        w, h = 140, 80
        big = supersample(w, h, f)
        for cx, cy, r in ((40, 52, 28), (72, 44, 34), (104, 54, 26)):
            pygame.draw.circle(big, (50, 126, 62), (cx * f, cy * f), r * f)
        for cx, cy, r in ((46, 46, 18), (80, 38, 20)):
            pygame.draw.circle(big, (76, 156, 84), (cx * f, cy * f), r * f)
        return shrink(big, f), (70, 78)
    if kind == "rock":
        w, h = 170, 120
        big = supersample(w, h, f)
        base = shade(theme["dirt"], 1.1) if theme["dirt"][0] < 200 else (150, 140, 130)
        base = lerp_color(base, (130, 130, 138), 0.55)
        pts = [(10, 118), (30, 62), (64, 26), (108, 18), (146, 56), (162, 118)]
        pygame.draw.polygon(big, shade(base, 0.8), [(x * f, y * f) for x, y in pts])
        lit = [(30, 62), (64, 26), (108, 18), (100, 66), (60, 90)]
        pygame.draw.polygon(big, shade(base, 1.15), [(x * f, y * f) for x, y in lit])
        pygame.draw.polygon(big, shade(base, 0.62),
                            [(x * f, y * f) for x, y in ((100, 66), (108, 18), (146, 56), (162, 118), (110, 118))])
        return shrink(big, f), (85, 116)
    if kind == "cactus":
        w, h = 110, 220
        big = supersample(w, h, f)
        g = (56, 140, 84)
        pygame.draw.rect(big, g, (int(42 * f), int(20 * f), int(26 * f), int(200 * f)), border_radius=int(13 * f))
        pygame.draw.rect(big, g, (int(8 * f), int(80 * f), int(20 * f), int(70 * f)), border_radius=int(10 * f))
        pygame.draw.rect(big, g, (int(8 * f), int(130 * f), int(48 * f), int(20 * f)), border_radius=int(10 * f))
        pygame.draw.rect(big, g, (int(82 * f), int(50 * f), int(20 * f), int(80 * f)), border_radius=int(10 * f))
        pygame.draw.rect(big, g, (int(55 * f), int(110 * f), int(45 * f), int(20 * f)), border_radius=int(10 * f))
        pygame.draw.rect(big, shade(g, 1.3), (int(48 * f), int(26 * f), int(7 * f), int(190 * f)), border_radius=int(4 * f))
        return shrink(big, f), (55, 218)
    # dead tree
    w, h = 170, 240
    big = supersample(w, h, f)
    col = (70, 52, 44) if theme["dirt"][0] > 90 else (50, 40, 48)
    pygame.draw.line(big, col, (85 * f, 240 * f), (85 * f, 90 * f), 12 * f)
    for (x0, y0, x1, y1, wd) in ((85, 150, 40, 90, 8), (85, 120, 135, 60, 8), (85, 95, 70, 30, 7),
                                 (110, 85, 150, 50, 5), (45, 98, 20, 70, 5)):
        pygame.draw.line(big, col, (x0 * f, y0 * f), (x1 * f, y1 * f), wd * f)
    return shrink(big, f), (85, 238)


# ---------------------------------------------------------------------------
# ground
# ---------------------------------------------------------------------------

CELL = 1024


def make_dirt_tile(theme, seed=5):
    rnd = random.Random(seed)
    base = theme["dirt"]
    size = 512
    tile = pygame.Surface((size, size), pygame.SRCALPHA)
    tile.fill(base)
    for _ in range(420):
        x, y = rnd.randint(0, size), rnd.randint(0, size)
        r = rnd.randint(2, 11)
        k = rnd.choice((0.72, 0.8, 0.88, 1.12, 1.22))
        pygame.draw.circle(tile, shade(base, k), (x, y), r)
    for _ in range(26):
        y = rnd.randint(0, size)
        pygame.draw.line(tile, shade(base, 0.86), (0, y), (size, y + rnd.randint(-8, 8)), rnd.randint(2, 5))
    return tile


class TerrainRenderer:
    """Pre-draws the ground into 1024x1024 pieces so drawing is fast."""

    def __init__(self, level, theme_name):
        self.level = level
        self.theme = THEMES[theme_name]
        self.tile = make_dirt_tile(self.theme)
        self.bottom = level.floor_y + 1200
        self.cells = {}            # (cx, cy) -> Surface (None = plain dirt)
        self._build()

    def _column_range(self, x0, x1):
        gmin, gmax, covered = 10 ** 9, -10 ** 9, True
        for chain in self.level.chains:
            if chain[-1][0] < x0 or chain[0][0] > x1:
                continue
            for x, y in chain:
                if x0 - 40 <= x <= x1 + 40:
                    gmin, gmax = min(gmin, y), max(gmax, y)
            if chain[0][0] > x0 or chain[-1][0] < x1:
                covered = False
        for a, b in self.level.gaps:
            if a < x1 and b > x0:
                covered = False
        return gmin, gmax, covered

    def _build(self):
        level = self.level
        cols = int(level.length // CELL) + 1
        top_cy = int((level.min_y - 400) // CELL)
        bottom_cy = int((level.max_y + 1200) // CELL)
        self.cols = cols
        self.top_cy = top_cy
        for cx in range(cols):
            x0, x1 = cx * CELL, (cx + 1) * CELL
            gmin, gmax, covered = self._column_range(x0, x1)
            if gmin > 10 ** 8:
                continue
            for cy in range(top_cy, bottom_cy + 1):
                y0, y1 = cy * CELL, (cy + 1) * CELL
                if y1 <= gmin - 30:
                    continue                           # all air
                if y0 >= gmax + 30 and covered:
                    self.cells[(cx, cy)] = None        # all dirt
                    continue
                self.cells[(cx, cy)] = self._make_cell(x0, y0)

    def _make_cell(self, x0, y0):
        t = self.theme
        cell = pygame.Surface((CELL, CELL), pygame.SRCALPHA)
        for tx in range(0, CELL, 512):
            for ty in range(0, CELL, 512):
                cell.blit(self.tile, (tx, ty))
        mask = pygame.Surface((CELL, CELL), pygame.SRCALPHA)
        rnd = random.Random(int(x0 * 7 + y0 * 13))
        for chain in self.level.chains:
            pts = [(x - x0, y - y0) for x, y in chain if x0 - 60 <= x <= x0 + CELL + 60]
            if len(pts) < 2:
                continue
            poly = pts + [(pts[-1][0], self.bottom - y0), (pts[0][0], self.bottom - y0)]
            pygame.draw.polygon(mask, (255, 255, 255, 255), poly)
            # grass / snow / sand edge on top of the ground
            for off, width, color in ((10, 24, t["edge"]), (6, 16, t["grass"]),
                                      (1, 5, shade(t["grass"], 1.28))):
                line = [(x, y + off) for x, y in pts]
                pygame.draw.lines(cell, color, False, line, width)
                for x, y in line[::2]:
                    pygame.draw.circle(cell, color, (x, y), width // 2)
            for x, y in pts[::2]:
                if rnd.random() < 0.7:
                    bx = x + rnd.randint(-6, 6)
                    h = rnd.randint(8, 16)
                    pygame.draw.polygon(cell, shade(t["grass"], rnd.uniform(1.0, 1.35)),
                                        [(bx - 3, y + 3), (bx + rnd.randint(-4, 4), y - h), (bx + 3, y + 3)])
        cell.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        # the grass lines were drawn before masking; draw them again on top
        for chain in self.level.chains:
            pts = [(x - x0, y - y0) for x, y in chain if x0 - 60 <= x <= x0 + CELL + 60]
            if len(pts) < 2:
                continue
            for off, width, color in ((10, 24, t["edge"]), (6, 16, t["grass"]),
                                      (1, 5, shade(t["grass"], 1.28))):
                line = [(x, y + off) for x, y in pts]
                pygame.draw.lines(cell, color, False, line, width)
                for x, y in line[::2]:
                    pygame.draw.circle(cell, color, (x, y), width // 2)
            for x, y in pts[::2]:
                if rnd.random() < 0.7:
                    bx = x + rnd.randint(-6, 6)
                    h = rnd.randint(8, 16)
                    pygame.draw.polygon(cell, shade(t["grass"], rnd.uniform(1.0, 1.35)),
                                        [(bx - 3, y + 3), (bx + rnd.randint(-4, 4), y - h), (bx + 3, y + 3)])
        return cell

    def draw(self, surf, cam_x, cam_y):
        cx0 = int(cam_x // CELL)
        cx1 = int((cam_x + W) // CELL)
        cy0 = int(cam_y // CELL)
        cy1 = int((cam_y + H) // CELL)
        for cx in range(cx0, cx1 + 1):
            for cy in range(cy0, cy1 + 1):
                key = (cx, cy)
                if key not in self.cells:
                    continue
                px, py = cx * CELL - cam_x, cy * CELL - cam_y
                cell = self.cells[key]
                if cell is None:
                    for tx in range(0, CELL, 512):
                        for ty in range(0, CELL, 512):
                            surf.blit(self.tile, (px + tx, py + ty))
                else:
                    surf.blit(cell, (px, py))


def place_decorations(level, theme_name, seed=3):
    """Choose where trees and rocks go. Returns (sprite, x, y) tuples."""
    t = THEMES[theme_name]
    rnd = random.Random(seed + level.number)
    out = []
    x = 100
    while x < level.length - 100:
        g = level.ground_y(x)
        if g is not None:
            kind = rnd.choice(t["deco"])
            sprite, anchor = make_deco(kind, t, rnd)
            s = rnd.uniform(0.75, 1.5) if kind not in ("bush", "rock") else rnd.uniform(0.8, 1.6)
            sprite = pygame.transform.smoothscale(
                sprite, (int(sprite.get_width() * s), int(sprite.get_height() * s)))
            out.append((sprite, x - anchor[0] * s, g + 14 - anchor[1] * s))
        x += rnd.randint(140, 360)
    return out


# ---------------------------------------------------------------------------
# obstacles
# ---------------------------------------------------------------------------

_obstacle_cache = {}


def log_sprite(r):
    key = ("log", r)
    if key in _obstacle_cache:
        return _obstacle_cache[key]
    f = 3
    size = r * 2 + 8
    big = supersample(size, size, f)
    c = size * f // 2
    pygame.draw.circle(big, (70, 44, 26), (c, c), r * f)
    pygame.draw.circle(big, (122, 80, 46), (c, c), int(r * f * 0.9))
    for i in range(1, 6):
        pygame.draw.circle(big, (150 - i * 6, 100 - i * 5, 60 - i * 3), (c, c), int(r * f * (0.9 - i * 0.14)), max(2, f))
    pygame.draw.circle(big, (90, 58, 34), (c, c), int(r * f * 0.12))
    img = shrink(big, f)
    _obstacle_cache[key] = img
    return img


def crate_sprite(size):
    key = ("crate", size)
    if key in _obstacle_cache:
        return _obstacle_cache[key]
    f = 3
    big = supersample(size, size, f)
    s = size * f
    pygame.draw.rect(big, (96, 62, 34), (0, 0, s, s), border_radius=5 * f)
    pygame.draw.rect(big, (190, 140, 82), (4 * f, 4 * f, s - 8 * f, s - 8 * f), border_radius=3 * f)
    for i in range(1, 4):
        y = i * s // 4
        pygame.draw.line(big, (150, 104, 58), (4 * f, y), (s - 4 * f, y), 2 * f)
    pygame.draw.line(big, (110, 72, 40), (6 * f, 6 * f), (s - 6 * f, s - 6 * f), 6 * f)
    pygame.draw.line(big, (110, 72, 40), (s - 6 * f, 6 * f), (6 * f, s - 6 * f), 6 * f)
    pygame.draw.rect(big, (96, 62, 34), (0, 0, s, s), 5 * f, border_radius=5 * f)
    img = shrink(big, f)
    _obstacle_cache[key] = img
    return img


def container_sprite(w, h, ramp, color):
    """A container with wooden ramps on both sides (matches the physics shape)."""
    key = ("container", w, h, color)
    if key in _obstacle_cache:
        return _obstacle_cache[key]
    f = 3
    tw = int(w + 2 * ramp) + 8
    big = supersample(tw, h + 8, f)
    ox = 4
    wood = (162, 112, 62)
    # ramps (drawn first, behind the container)
    left = [(ox * f, (h + 4) * f), ((ox + ramp) * f, 4 * f), ((ox + ramp) * f, (h + 4) * f)]
    right = [((ox + ramp + w) * f, 4 * f), ((ox + 2 * ramp + w) * f, (h + 4) * f), ((ox + ramp + w) * f, (h + 4) * f)]
    for poly in (left, right):
        pygame.draw.polygon(big, shade(wood, 0.8), poly)
    for i in range(1, 6):
        t = i / 6
        pygame.draw.line(big, shade(wood, 0.6), (ox * f + t * ramp * f, (h + 4) * f),
                         (ox * f + t * ramp * f, (h + 4 - t * h) * f), 2 * f)
        xr = (ox + ramp + w + (1 - t) * ramp) * f
        pygame.draw.line(big, shade(wood, 0.6), (xr, (h + 4) * f), (xr, (h + 4 - (1 - t) * h) * f), 2 * f)
    body = pygame.Rect((ox + ramp) * f, 4 * f, w * f, h * f)
    pygame.draw.rect(big, shade(color, 0.7), body, border_radius=3 * f)
    inner = body.inflate(-6 * f, -6 * f)
    pygame.draw.rect(big, color, inner, border_radius=2 * f)
    n = max(4, int(w // 18))
    for i in range(1, n):
        x = inner.x + i * inner.w // n
        pygame.draw.line(big, shade(color, 0.78), (x, inner.y), (x, inner.bottom), 3 * f)
        pygame.draw.line(big, shade(color, 1.18), (x + 3 * f, inner.y), (x + 3 * f, inner.bottom), f)
    pygame.draw.rect(big, shade(color, 0.55), body, 4 * f, border_radius=3 * f)
    img = shrink(big, f)
    _obstacle_cache[key] = img
    return img


def plank_sprite(w, h):
    key = ("plank", w, h)
    if key in _obstacle_cache:
        return _obstacle_cache[key]
    f = 3
    big = supersample(w, h + 140, f)
    for x in (30, w - 30):
        pygame.draw.rect(big, (84, 56, 34), ((x - 10) * f, h * f, 20 * f, 130 * f))
    pygame.draw.rect(big, (130, 90, 52), (0, 0, w * f, h * f), border_radius=4 * f)
    for i in range(1, int(w // 60)):
        pygame.draw.line(big, (92, 62, 36), (i * 60 * f, 0), (i * 60 * f, h * f), 3 * f)
    pygame.draw.rect(big, (160, 118, 70), (0, 0, w * f, 5 * f), border_radius=3 * f)
    pygame.draw.rect(big, (70, 46, 28), (0, 0, w * f, h * f), 3 * f, border_radius=4 * f)
    img = shrink(big, f)
    _obstacle_cache[key] = img
    return img


CONTAINER_COLORS = [(200, 62, 52), (52, 112, 190), (70, 150, 84), (220, 160, 48)]


def skin_sprite(w, h, color):
    """A container drawn over a flat raised piece of ground."""
    key = ("skin", w, h, color)
    if key in _obstacle_cache:
        return _obstacle_cache[key]
    f = 2
    big = supersample(w, h, f)
    body = pygame.Rect(0, 0, w * f, h * f)
    pygame.draw.rect(big, shade(color, 0.62), body, border_radius=4 * f)
    inner = body.inflate(-8 * f, -8 * f)
    pygame.draw.rect(big, color, inner, border_radius=3 * f)
    n = max(6, int(w // 22))
    for i in range(1, n):
        x = inner.x + i * inner.w // n
        pygame.draw.line(big, shade(color, 0.76), (x, inner.y), (x, inner.bottom), 4 * f)
        pygame.draw.line(big, shade(color, 1.2), (x + 4 * f, inner.y), (x + 4 * f, inner.bottom), f)
    pygame.draw.rect(big, shade(color, 0.5), body, 5 * f, border_radius=4 * f)
    img = shrink(big, f)
    _obstacle_cache[key] = img
    return img


# ---------------------------------------------------------------------------
# the bike and rider
# ---------------------------------------------------------------------------

class BikeArt:
    """Pre-drawn bike body, rider and wheel for one bike at one size."""

    BODY = (280, 240)      # sprite sizes (at scale 1), centre = frame centre
    RIDER = (260, 260)     # centre = rider's hips
    WHEEL = (66, 66)

    def __init__(self, spec, scale=1.0):
        self.scale = scale
        self.spec = spec
        f = 3.0 * scale
        self.body = self._make_body(spec, f)
        self.rider = self._make_rider(spec, f)
        self.wheel = self._make_wheel(spec, f)

    # -- parts --
    def _big(self, size, f):
        return pygame.Surface((int(size[0] * f), int(size[1] * f)), pygame.SRCALPHA)

    def _fit(self, big, size):
        return pygame.transform.smoothscale(
            big, (max(1, int(size[0] * self.scale)), max(1, int(size[1] * self.scale))))

    def _make_body(self, spec, f):
        color, dark = spec["color"], spec["dark"]
        big = self._big(self.BODY, f)
        cx, cy = self.BODY[0] / 2, self.BODY[1] / 2

        def P(x, y):
            return ((cx + x) * f, (cy + y) * f)

        def poly(col, pts):
            pygame.draw.polygon(big, col, [P(*p) for p in pts])

        def line(col, a, b, w):
            pygame.draw.line(big, col, P(*a), P(*b), int(w * f))

        # exhaust pipe
        line((120, 122, 134), (14, 24), (-84, 2), 9)
        line((176, 178, 190), (14, 22), (-84, 0), 3)
        pygame.draw.circle(big, (70, 72, 82), P(-86, 1), int(7 * f))
        # engine
        poly((46, 48, 56), [(-18, 2), (38, 2), (42, 30), (-14, 32)])
        for i in range(4):
            line((86, 88, 100), (-14 + i * 2, 8 + i * 6), (38 + i * 1, 8 + i * 6), 2)
        pygame.draw.circle(big, (120, 122, 134), P(10, 18), int(8 * f))
        pygame.draw.circle(big, (60, 62, 72), P(10, 18), int(4 * f))
        # frame tubes
        line((30, 30, 36), (-60, -18), (-8, 24), 6)
        line((30, 30, 36), (30, -20), (36, 24), 6)
        # rear fender
        poly(color, [(-96, -22), (-66, -40), (-42, -32), (-62, -24), (-90, -10)])
        poly(dark, [(-96, -22), (-90, -10), (-62, -24), (-72, -28)])
        # seat
        poly((28, 28, 34), [(-74, -36), (-30, -40), (-20, -30), (-68, -24)])
        poly((52, 52, 60), [(-74, -36), (-30, -40), (-28, -37), (-72, -33)])
        # tank
        poly(dark, [(-26, -30), (30, -38), (54, -22), (46, -2), (14, 0), (-14, -8)])
        poly(color, [(-26, -32), (30, -42), (54, -26), (44, -10), (10, -10), (-14, -16)])
        poly(shade(color, 1.35), [(-14, -32), (24, -40), (38, -34), (-6, -26)])
        # number plate + headlight
        pygame.draw.circle(big, (250, 250, 250), P(64, -46), int(17 * f))
        pygame.draw.circle(big, dark, P(64, -46), int(17 * f), int(3 * f))
        num = font(int(24 * f)).render(str(spec["power"] if spec["power"] < 10 else 0), True, (20, 20, 24))
        big.blit(num, num.get_rect(center=P(64, -45)))
        pygame.draw.circle(big, (255, 244, 190), P(76, -30), int(7 * f))
        pygame.draw.circle(big, (255, 255, 240), P(77, -31), int(3 * f))
        # handlebar
        line((24, 24, 28), (50, -52), (68, -66), 6)
        pygame.draw.circle(big, (20, 20, 24), P(68, -66), int(6 * f))
        return self._fit(big, self.BODY)

    def _make_rider(self, spec, f):
        color, dark = spec["color"], spec["dark"]
        big = self._big(self.RIDER, f)
        cx, cy = self.RIDER[0] / 2, self.RIDER[1] / 2

        def P(x, y):
            return ((cx + x) * f, (cy + y) * f)

        def limb(col, pts, w):
            for a, b in zip(pts, pts[1:]):
                pygame.draw.line(big, col, P(*a), P(*b), int(w * f))
            for p in pts:
                pygame.draw.circle(big, col, P(*p), int(w * f / 2))

        pants, boots, glove = (34, 40, 66), (24, 24, 30), (30, 30, 36)
        # legs
        limb(pants, [(0, 0), (40, 4), (38, 42)], 17)
        pygame.draw.polygon(big, boots, [P(26, 38), P(60, 38), P(64, 52), P(26, 54)])
        # torso
        limb(color, [(0, -2), (28, -52)], 28)
        limb(shade(color, 1.18), [(4, -8), (30, -50)], 8)
        # arms
        limb(dark, [(28, -52), (62, -42), (90, -26)], 12)
        pygame.draw.circle(big, glove, P(92, -25), int(8 * f))
        # head and helmet
        pygame.draw.circle(big, (240, 240, 245), P(38, -82), int(17 * f))
        pygame.draw.circle(big, color, P(36, -86), int(17 * f), int(5 * f))
        pygame.draw.polygon(big, (30, 36, 52), [P(40, -90), P(58, -84), P(56, -72), P(42, -74)])
        pygame.draw.polygon(big, shade(color, 1.1), [P(20, -88), P(40, -100), P(46, -92), P(30, -84)])
        return self._fit(big, self.RIDER)

    def _make_wheel(self, spec, f):
        big = self._big(self.WHEEL, f)
        c = (self.WHEEL[0] / 2 * f, self.WHEEL[1] / 2 * f)
        pygame.draw.circle(big, (18, 18, 22), c, int(30 * f))
        for i in range(24):                                   # tread blocks
            a = i * math.tau / 24
            p1 = (c[0] + math.cos(a) * 25 * f, c[1] + math.sin(a) * 25 * f)
            p2 = (c[0] + math.cos(a) * 31 * f, c[1] + math.sin(a) * 31 * f)
            pygame.draw.line(big, (52, 52, 58), p1, p2, int(4 * f))
        pygame.draw.circle(big, (40, 40, 46), c, int(25 * f))
        pygame.draw.circle(big, (190, 192, 204), c, int(19 * f))
        pygame.draw.circle(big, (66, 68, 78), c, int(16 * f))
        for i in range(8):
            a = i * math.tau / 8
            pygame.draw.line(big, (170, 172, 184), c,
                             (c[0] + math.cos(a) * 17 * f, c[1] + math.sin(a) * 17 * f), int(2.2 * f))
        pygame.draw.circle(big, self.spec["color"], c, int(6 * f))
        pygame.draw.circle(big, (240, 240, 245), (c[0] + 2 * f, c[1] - 2 * f), int(1.8 * f))
        return self._fit(big, self.WHEEL)

    # -- drawing --
    def draw(self, surf, origin, angle, rear_local, front_local, rear_ang, front_ang,
             lean=0.0, show_rider=True):
        s = self.scale
        ca, sa = math.cos(angle), math.sin(angle)

        def to_screen(lx, ly):
            return (origin[0] + (lx * ca - ly * sa) * s, origin[1] + (lx * sa + ly * ca) * s)

        rear_s, front_s = to_screen(*rear_local), to_screen(*front_local)
        for pos, ang in ((rear_s, rear_ang), (front_s, front_ang)):
            img = pygame.transform.rotozoom(self.wheel, -math.degrees(ang), 1.0)
            surf.blit(img, img.get_rect(center=pos))
        w = max(2, int(9 * s))
        pygame.draw.line(surf, (34, 34, 42), to_screen(-34, 16), rear_s, w)
        pygame.draw.line(surf, (96, 98, 110), to_screen(-34, 16), rear_s, max(1, int(3 * s)))
        shock_top = to_screen(-46, -22)
        shock_bot = to_screen(-34 + (rear_local[0] + 34) * 0.7, 16 + (rear_local[1] - 16) * 0.7)
        pygame.draw.line(surf, (230, 190, 40), shock_top, shock_bot, max(2, int(6 * s)))
        top = to_screen(56, -44)
        pygame.draw.line(surf, (214, 216, 226), top, front_s, max(2, int(9 * s)))
        pygame.draw.line(surf, (130, 132, 148), top, front_s, max(1, int(3 * s)))
        body = pygame.transform.rotozoom(self.body, -math.degrees(angle), 1.0)
        surf.blit(body, body.get_rect(center=origin))
        if show_rider:
            hip = to_screen(-32, -36)
            rider = pygame.transform.rotozoom(self.rider, -math.degrees(angle + lean), 1.0)
            surf.blit(rider, rider.get_rect(center=hip))
        # front fender (an arc over the front wheel)
        pts = []
        for i in range(11):
            a = math.radians(-150 + i * 11) + angle
            pts.append((front_s[0] + math.cos(a) * 37 * s, front_s[1] + math.sin(a) * 37 * s))
        pygame.draw.lines(surf, self.spec["color"], False, pts, max(2, int(7 * s)))


_art_cache = {}


def bike_art(spec, scale=1.0):
    key = (spec["id"], scale)
    if key not in _art_cache:
        _art_cache[key] = BikeArt(spec, scale)
    return _art_cache[key]


# ---------------------------------------------------------------------------
# UI pieces
# ---------------------------------------------------------------------------

def draw_panel(surf, rect, color=(24, 20, 50), border=(150, 120, 255), alpha=235, radius=22):
    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(panel, (*color, alpha), panel.get_rect(), border_radius=radius)
    pygame.draw.rect(panel, border, panel.get_rect(), 3, border_radius=radius)
    surf.blit(panel, rect.topleft)


def draw_button(surf, rect, label, hover=False, enabled=True, color=(255, 140, 20), size=44):
    if not enabled:
        color = (96, 96, 108)
    base = shade(color, 1.18) if hover and enabled else color
    r = rect.copy()
    if hover and enabled:
        r.inflate_ip(10, 6)
    shadow = r.move(0, 6)
    draw_rect_alpha(surf, (0, 0, 0, 90), shadow, 18)
    pygame.draw.rect(surf, shade(base, 0.62), r.move(0, 5), border_radius=18)
    pygame.draw.rect(surf, base, r, border_radius=18)
    hl = pygame.Rect(r.x + 6, r.y + 5, r.w - 12, r.h // 2 - 4)
    top = pygame.Surface(hl.size, pygame.SRCALPHA)
    pygame.draw.rect(top, (255, 255, 255, 55), top.get_rect(), border_radius=14)
    surf.blit(top, hl)
    pygame.draw.rect(surf, shade(base, 0.5), r, 3, border_radius=18)
    draw_text(surf, label, size, (255, 255, 255) if enabled else (200, 200, 208), r.center, shadow=3)


def make_coin(r, squash=1.0):
    big = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
    c = r * 2
    pygame.draw.circle(big, (176, 118, 10), (c, c), r * 2)
    pygame.draw.circle(big, (255, 206, 52), (c, c), int(r * 1.78))
    pygame.draw.circle(big, (255, 232, 120), (c, c), int(r * 1.3))
    pygame.draw.circle(big, (240, 184, 30), (c, c), int(r * 1.3), max(2, r // 5))
    star_pts = []
    for i in range(10):
        rad = r * (0.85 if i % 2 == 0 else 0.38)
        a = -math.pi / 2 + i * math.pi / 5
        star_pts.append((c + math.cos(a) * rad, c + math.sin(a) * rad))
    pygame.draw.polygon(big, (214, 150, 10), star_pts)
    w = max(2, int(r * 2 * squash))
    return pygame.transform.smoothscale(big, (w, r * 2))


def coin_frames(r, n=12):
    return [make_coin(r, 0.12 + 0.88 * i / (n - 1)) for i in range(n)]


def draw_coin(surf, pos, r, squash=1.0):
    img = make_coin(r, squash)
    surf.blit(img, img.get_rect(center=pos))


def draw_star(surf, pos, r, filled=True, angle=0.0):
    pts = []
    for i in range(10):
        rad = r * (1.0 if i % 2 == 0 else 0.46)
        a = -math.pi / 2 + i * math.pi / 5 + angle
        pts.append((pos[0] + math.cos(a) * rad, pos[1] + math.sin(a) * rad))
    if filled:
        pygame.draw.polygon(surf, (255, 214, 60), pts)
        pygame.draw.polygon(surf, (190, 120, 10), pts, max(2, int(r / 8)))
    else:
        pygame.draw.polygon(surf, (50, 46, 74), pts)
        pygame.draw.polygon(surf, (96, 90, 130), pts, max(2, int(r / 8)))


def draw_lock(surf, pos, size):
    x, y = pos
    w = size
    pygame.draw.arc(surf, (210, 210, 220), (x - w * 0.32, y - w * 0.62, w * 0.64, w * 0.8), 0, math.pi, max(4, int(w * 0.12)))
    pygame.draw.rect(surf, (230, 190, 60), (x - w * 0.45, y - w * 0.18, w * 0.9, w * 0.7), border_radius=int(w * 0.12))
    pygame.draw.circle(surf, (90, 60, 10), (x, y + w * 0.12), int(w * 0.1))


def draw_keycap(surf, rect, label, pressed=False, size=40):
    r = rect.copy()
    if pressed:
        r.y += 5
    pygame.draw.rect(surf, (20, 18, 36), rect.move(0, 6), border_radius=12)
    color = (255, 168, 40) if pressed else (236, 236, 244)
    pygame.draw.rect(surf, shade(color, 0.7), r.move(0, 4), border_radius=12)
    pygame.draw.rect(surf, color, r, border_radius=12)
    draw_text(surf, label, size, (40, 36, 60), r.center, shadow=0)


def draw_dial(surf, center, radius, speed_kmh, max_kmh=180):
    """The speedometer (bottom right)."""
    cx, cy = center
    pygame.draw.circle(surf, (20, 18, 28), center, radius + 14)
    pygame.draw.circle(surf, (230, 140, 30), center, radius + 14, 8)
    pygame.draw.circle(surf, (36, 34, 46), center, radius)
    pygame.draw.circle(surf, (70, 66, 86), center, radius, 3)
    start, end = 135, 405
    for i in range(0, 10):
        a = math.radians(start + (end - start) * i / 9)
        r1, r2 = radius - 10, radius - 28
        col = (255, 90, 60) if i >= 8 else (230, 230, 240)
        pygame.draw.line(surf, col, (cx + math.cos(a) * r1, cy + math.sin(a) * r1),
                         (cx + math.cos(a) * r2, cy + math.sin(a) * r2), 5)
        if i % 3 == 0:
            lab = font(22).render(str(int(max_kmh * i / 9)), True, (200, 200, 214))
            surf.blit(lab, lab.get_rect(center=(cx + math.cos(a) * (radius - 50), cy + math.sin(a) * (radius - 50))))
    k = clamp(speed_kmh / max_kmh, 0, 1)
    a = math.radians(start + (end - start) * k)
    tip = (cx + math.cos(a) * (radius - 18), cy + math.sin(a) * (radius - 18))
    tail = (cx - math.cos(a) * 18, cy - math.sin(a) * 18)
    pygame.draw.line(surf, (255, 70, 50), tail, tip, 7)
    pygame.draw.circle(surf, (220, 220, 230), center, 14)
    pygame.draw.circle(surf, (60, 60, 72), center, 7)
    draw_text(surf, f"{int(speed_kmh)}", 36, (255, 255, 255), (cx, cy + radius * 0.5), shadow=2)
    draw_text(surf, "km/h", 20, (170, 170, 186), (cx, cy + radius * 0.5 + 28), shadow=0)


def draw_flag(surf, x, y, active, t, height=170):
    """A checkpoint flag. (x, y) is the bottom of the pole."""
    draw_shadow(surf, (x - 26, y - 6, 52, 14), 80)
    pygame.draw.line(surf, (70, 70, 80), (x, y), (x, y - height), 7)
    pygame.draw.circle(surf, (220, 220, 230), (x, y - height), 8)
    color = (60, 200, 90) if active else (230, 60, 50)
    pts = [(x + 3, y - height + 8)]
    for i in range(1, 7):
        wave = math.sin(t * 6 + i * 0.7) * 6 * (i / 6)
        pts.append((x + 3 + i * 14, y - height + 8 + wave))
    top = list(pts)
    bottom = [(px, py + 44 - (i * 3)) for i, (px, py) in enumerate(pts)]
    pygame.draw.polygon(surf, color, top + bottom[::-1])
    pygame.draw.polygon(surf, shade(color, 0.6), top + bottom[::-1], 3)
