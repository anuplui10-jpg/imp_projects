# levels.py
# Level data. Each level is built from simple pieces (flat, rise, hill, ramp,
# gap...) plus obstacles, coins and checkpoints. Easy to edit!
#
# World coordinates: x goes right, y goes DOWN (so "up" means smaller y).

import bisect
import math

STEP = 16          # distance between ground points


class Builder:
    """Builds the ground and the things on it, one piece after another."""

    def __init__(self, y=900):
        self.chains = []           # separate pieces of ground (gaps split them)
        self.gaps = []             # (x0, x1) holes in the ground
        self.pts = [(0.0, float(y))]
        self.obstacles = []
        self.coins = []
        self.checkpoints = []
        self.skins = []            # decorations drawn over flat ground (containers...)
        self.finish_x = None

    # ----- position -----
    @property
    def x(self):
        return self.pts[-1][0]

    @property
    def y(self):
        return self.pts[-1][1]

    # ----- ground pieces -----
    def flat(self, length):
        x0, y0 = self.x, self.y
        n = max(1, int(round(length / STEP)))
        for i in range(1, n + 1):
            self.pts.append((x0 + length * i / n, y0))

    def rise(self, length, dy, shape="smooth"):
        """Go up by dy (negative = go down) over `length` pixels."""
        x0, y0 = self.x, self.y
        n = max(2, int(round(length / STEP)))
        for i in range(1, n + 1):
            t = i / n
            if shape == "smooth":
                f = (1 - math.cos(math.pi * t)) / 2
            elif shape == "ramp":
                f = t ** 1.8
            else:
                f = t
            self.pts.append((x0 + length * t, y0 - dy * f))

    def hill(self, length, height):
        self.rise(length / 2, height)
        self.rise(length / 2, -height)

    def bumps(self, count, width, height):
        for _ in range(count):
            self.hill(width, height)

    def ramp(self, length, height):
        self.rise(length, height, "ramp")

    def gap(self, width, land_dy=0):
        """A hole in the ground. land_dy > 0 means the far side is higher."""
        self.chains.append(self.pts)
        self.gaps.append((self.x, self.x + width))
        x, y = self.x + width, self.y - land_dy
        self.pts = [(x, y)]

    def platform(self, length, skin="container"):
        """Flat raised ground that is drawn like a container, truck, etc."""
        x0 = self.x
        self.flat(length)
        self.skins.append({"x0": x0, "x1": self.x, "kind": skin})

    def bridge(self, width):
        """A wooden plank over a hole."""
        y = self.y
        x = self.x
        self.gap(width, 0)
        self.obstacles.append({"type": "block", "kind": "plank", "x": x + width / 2,
                               "w": width + 60, "h": 18, "ref_y": y + 9, "fixed": True})

    # ----- things on the ground (offset is measured from the current x) -----
    def log(self, offset, r):
        self.obstacles.append({"type": "log", "x": self.x + offset, "r": r})

    def block(self, offset, w, h, kind="stone"):
        self.obstacles.append({"type": "block", "kind": kind, "x": self.x + offset,
                               "w": w, "h": h})

    def crates(self, offset, cols, rows):
        self.obstacles.append({"type": "crates", "x": self.x + offset,
                               "cols": cols, "rows": rows})

    def coin_line(self, offset, count, spacing, height):
        for i in range(count):
            self.coins.append({"x": self.x + offset + i * spacing, "h": height, "ref": self.y})

    def coin_arc(self, offset, count, spacing, base_h, arc_h):
        for i in range(count):
            t = i / max(1, count - 1)
            self.coins.append({"x": self.x + offset + i * spacing,
                               "h": base_h + arc_h * math.sin(math.pi * t),
                               "ref": self.y})

    def checkpoint(self, offset=0):
        self.checkpoints.append(self.x + offset)

    def finish(self):
        self.finish_x = self.x + 120
        self.flat(700)


class Level:
    def __init__(self, number, name, theme, builder, par):
        self.number = number
        self.name = name
        self.theme = theme
        self.par = par                     # seconds for 3 stars / 2 stars
        self.start_x = 320
        b = builder
        b.chains.append(b.pts)
        self.chains = b.chains
        self.gaps = b.gaps
        self.skins = b.skins
        self.finish_x = b.finish_x
        self.checkpoints = list(b.checkpoints)
        self._xs = [[p[0] for p in chain] for chain in self.chains]
        self.length = self.chains[-1][-1][0]
        self.floor_y = max(p[1] for c in self.chains for p in c) + 900
        self.min_y = min(p[1] for c in self.chains for p in c)
        self.max_y = max(p[1] for c in self.chains for p in c)

        # work out heights for obstacles and coins now that the ground exists
        self.obstacles = []
        for ob in b.obstacles:
            ob = dict(ob)
            if ob["type"] == "log":
                g = self.ground_y(ob["x"])
                if g is None:
                    continue
                ob["y"] = g - ob["r"] * 0.2          # sunk a little into the ground
            elif ob["type"] == "block":
                if ob.get("fixed"):
                    ob["y"] = ob["ref_y"]
                else:
                    g = self.ground_y(ob["x"])
                    if g is None:
                        continue
                    ob["y"] = g - ob["h"] / 2 + 3
            elif ob["type"] == "crates":
                g = self.ground_y(ob["x"])
                if g is None:
                    continue
                ob["y"] = g
            self.obstacles.append(ob)
        self.coins = []
        for c in b.coins:
            g = self.ground_y(c["x"])
            if g is None:
                g = c["ref"]
            self.coins.append({"x": c["x"], "y": g - c["h"]})

    # ----- ground queries -----
    def ground_y(self, x):
        for chain, xs in zip(self.chains, self._xs):
            if xs[0] <= x <= xs[-1]:
                i = min(bisect.bisect_right(xs, x) - 1, len(xs) - 2)
                (x0, y0), (x1, y1) = chain[i], chain[i + 1]
                t = (x - x0) / (x1 - x0) if x1 > x0 else 0.0
                return y0 + (y1 - y0) * t
        return None

    def slope_angle(self, x):
        a, b = self.ground_y(x - 25), self.ground_y(x + 25)
        if a is None or b is None:
            return 0.0
        return math.atan2(b - a, 50.0)


# ---------------------------------------------------------------------------
# THE LEVELS
# ---------------------------------------------------------------------------

def level_1():
    b = Builder()
    b.coin_line(500, 5, 90, 80)
    b.flat(900)
    b.rise(450, 100)
    b.coin_line(-250, 3, 70, 90)
    b.flat(200)
    b.rise(450, -100)
    b.flat(250)
    b.log(200, 24)
    b.coin_line(150, 3, 70, 100)
    b.flat(700)
    b.checkpoint()
    b.bumps(4, 260, 34)
    b.flat(250)
    b.log(100, 28)
    b.log(450, 30)
    b.flat(850)
    b.checkpoint()
    b.flat(900)
    b.ramp(260, 85)
    b.coin_arc(60, 5, 60, 110, 70)
    b.gap(190, -45)
    b.rise(300, -35, "linear")
    b.flat(600)
    b.checkpoint()
    b.rise(500, 150)
    b.coin_line(-300, 4, 70, 90)
    b.flat(300)
    b.rise(450, -150)
    b.flat(300)
    b.crates(150, 1, 2)
    b.flat(900)
    b.finish()
    return Level(1, "FOREST TRAIL", "forest", b, (24.0, 36.0))


def level_2():
    b = Builder()
    b.coin_line(500, 5, 90, 80)
    b.flat(900)
    b.hill(900, 150)
    b.flat(300)
    b.log(100, 32)
    b.log(500, 36)
    b.flat(900)
    b.checkpoint()
    b.rise(240, 70, "linear")
    b.platform(420, "container")
    b.coin_line(-380, 4, 80, 90)
    b.rise(240, -70, "linear")
    b.flat(500)
    b.bumps(5, 220, 42)
    b.flat(300)
    b.checkpoint()
    b.flat(800)
    b.ramp(280, 95)
    b.coin_arc(60, 5, 60, 110, 70)
    b.gap(230, -50)
    b.rise(320, -45, "linear")
    b.flat(500)
    b.rise(700, 260)
    b.flat(300)
    b.log(100, 34)
    b.flat(500)
    b.checkpoint()
    b.rise(600, -260)
    b.flat(300)
    b.crates(100, 2, 2)
    b.flat(800)
    b.finish()
    return Level(2, "ROCKY HILLS", "rocky", b, (28.0, 42.0))


def level_3():
    b = Builder()
    b.coin_line(500, 5, 90, 80)
    b.flat(900)
    b.block(150, 200, 52, "container")
    b.flat(700)
    b.crates(100, 1, 2)
    b.flat(700)
    b.checkpoint()
    b.flat(800)
    b.ramp(260, 85)
    b.coin_arc(50, 5, 60, 110, 70)
    b.bridge(300)
    b.flat(500)
    b.log(100, 30)
    b.log(400, 34)
    b.log(700, 36)
    b.flat(1000)
    b.checkpoint()
    b.rise(240, 80, "linear")
    b.platform(500, "container")
    b.coin_line(-420, 4, 90, 90)
    b.rise(240, -80, "linear")
    b.flat(400)
    b.crates(100, 2, 2)
    b.flat(700)
    b.bumps(4, 270, 38)
    b.flat(300)
    b.checkpoint()
    b.flat(900)
    b.ramp(300, 100)
    b.gap(250, -60)
    b.rise(350, -40, "linear")
    b.flat(600)
    b.block(100, 220, 56, "container")
    b.flat(800)
    b.finish()
    return Level(3, "JUNKYARD", "dusk", b, (42.0, 62.0))


def level_4():
    b = Builder()
    b.coin_line(500, 5, 90, 80)
    b.flat(900)
    b.hill(1100, 220)
    b.flat(300)
    b.hill(900, 160)
    b.flat(600)
    b.checkpoint()
    b.flat(500)
    b.ramp(300, 100)
    b.coin_arc(40, 6, 70, 110, 80)
    b.gap(235, -70)
    b.rise(400, -40, "linear")
    b.flat(700)
    b.log(100, 34)
    b.log(500, 38)
    b.flat(800)
    b.checkpoint()
    b.rise(800, 300)
    b.flat(300)
    b.rise(700, -300)
    b.flat(400)
    b.crates(100, 2, 2)
    b.flat(500)
    b.checkpoint()
    b.flat(1000)
    b.ramp(320, 110)
    b.coin_arc(40, 6, 80, 130, 120)
    b.gap(300, -330)
    b.rise(600, -60, "linear")
    b.flat(900)
    b.finish()
    return Level(4, "DESERT CANYON", "desert", b, (30.0, 46.0))


def level_5():
    b = Builder()
    b.coin_line(500, 5, 90, 80)
    b.flat(900)
    b.rise(800, 280)
    b.flat(300)
    b.log(100, 36)
    b.flat(400)
    b.rise(600, -200)
    b.flat(400)
    b.checkpoint()
    b.bumps(6, 220, 50)
    b.flat(400)
    b.log(100, 36)
    b.log(450, 40)
    b.flat(800)
    b.checkpoint()
    b.flat(900)
    b.ramp(300, 100)
    b.coin_arc(40, 6, 70, 110, 80)
    b.gap(240, -70)
    b.rise(400, -40, "linear")
    b.flat(500)
    b.rise(900, 350)
    b.flat(300)
    b.crates(100, 2, 2)
    b.flat(500)
    b.checkpoint()
    b.rise(700, -350)
    b.flat(500)
    b.finish()
    return Level(5, "SNOWY PEAK", "snow", b, (30.0, 46.0))


def level_6():
    b = Builder()
    b.coin_line(500, 5, 90, 80)
    b.flat(900)
    for _ in range(3):
        b.rise(120, 60, "linear")
        b.flat(240)
    b.coin_line(-300, 4, 80, 90)
    b.rise(200, -180, "linear")
    b.flat(500)
    b.checkpoint()
    b.flat(800)
    b.ramp(300, 100)
    b.coin_arc(40, 6, 70, 110, 80)
    b.gap(250, -50)
    b.flat(400)
    b.block(100, 200, 60, "container")
    b.crates(520, 2, 2)
    b.flat(1000)
    b.checkpoint()
    b.log(100, 32)
    b.log(450, 36)
    b.log(800, 34)
    b.flat(1100)
    b.bridge(360)
    b.flat(600)
    b.checkpoint()
    b.flat(900)
    b.ramp(320, 110)
    b.gap(270, -80)
    b.rise(400, -50, "linear")
    b.flat(500)
    b.crates(100, 2, 2)
    b.flat(800)
    b.finish()
    return Level(6, "NIGHT QUARRY", "night", b, (40.0, 60.0))


def level_7():
    b = Builder()
    b.coin_line(500, 6, 90, 80)
    b.flat(900)
    b.bumps(5, 240, 55)
    b.flat(400)
    b.log(100, 36)
    b.log(450, 40)
    b.log(800, 36)
    b.flat(1100)
    b.checkpoint()
    b.flat(900)
    b.ramp(340, 120)
    b.coin_arc(40, 6, 70, 120, 90)
    b.gap(290, -90)
    b.rise(420, -50, "linear")
    b.flat(600)
    b.checkpoint()
    b.rise(240, 90, "linear")
    b.platform(440, "container")
    b.rise(200, 90, "linear")
    b.platform(440, "container")
    b.rise(240, -180, "linear")
    b.flat(500)
    b.crates(100, 2, 2)
    b.flat(700)
    b.checkpoint()
    b.rise(1000, 340)
    b.flat(500)
    b.ramp(340, 120)
    b.gap(300, -90)
    b.rise(600, -300, "smooth")
    b.flat(600)
    b.checkpoint()
    b.log(100, 40)
    b.log(500, 38)
    b.flat(900)
    b.finish()
    return Level(7, "VOLCANO RUN", "volcano", b, (46.0, 70.0))


LEVEL_BUILDERS = [level_1, level_2, level_3, level_4, level_5, level_6, level_7]
LEVEL_NAMES = ["FOREST TRAIL", "ROCKY HILLS", "JUNKYARD", "DESERT CANYON",
               "SNOWY PEAK", "NIGHT QUARRY", "VOLCANO RUN"]


def build_level(index):
    return LEVEL_BUILDERS[index]()
