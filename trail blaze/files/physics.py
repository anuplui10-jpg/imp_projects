# physics.py
# The physics world: terrain, obstacles and the bike (two wheels with
# suspension, a frame and an engine). It uses the pymunk library and does
# not need pygame, so it can also be tested without a window.

import math

import pymunk
from pymunk import Vec2d

from bikes import physics_for

GRAVITY = 1800.0
SUBSTEPS = 4                 # physics steps per frame (smoother and safer)
CAT_BIKE = 0b01
CAT_WORLD = 0b10
ALL = 0xFFFFFFFF

WORLD_FILTER = pymunk.ShapeFilter(categories=CAT_WORLD, mask=ALL)
BIKE_FILTER = pymunk.ShapeFilter(group=1, categories=CAT_BIKE, mask=CAT_WORLD)
QUERY_FILTER = pymunk.ShapeFilter(mask=CAT_WORLD)

SURFACE = 5.0                # thickness of the ground segments
CRATE = 56                   # crate size in pixels


class World:
    """Holds the pymunk space for one level."""

    def __init__(self, level):
        self.level = level
        self.space = pymunk.Space()
        self.space.gravity = (0, GRAVITY)
        self.space.iterations = 24
        self.space.sleep_time_threshold = 0.6
        self.crates = []          # (body, shape)
        self.crate_start = []     # where each crate began
        self.ragdoll = None
        self._build_terrain()
        self._build_obstacles()

    # ----- building -----
    def _build_terrain(self):
        static = self.space.static_body
        shapes = []
        for chain in self.level.chains:
            for (x0, y0), (x1, y1) in zip(chain, chain[1:]):
                seg = pymunk.Segment(static, (x0, y0 + SURFACE), (x1, y1 + SURFACE), SURFACE)
                seg.friction = 1.0
                seg.elasticity = 0.0
                seg.filter = WORLD_FILTER
                shapes.append(seg)
            # walls at both ends so the bike cannot slip into a pit edge
            for x, y in (chain[0], chain[-1]):
                wall = pymunk.Segment(static, (x, y + SURFACE), (x, y + 2500), SURFACE)
                wall.friction = 0.6
                wall.filter = WORLD_FILTER
                shapes.append(wall)
        self.space.add(*shapes)

    def _build_obstacles(self):
        static = self.space.static_body
        for ob in self.level.obstacles:
            kind = ob["type"]
            if kind == "log":
                shape = pymunk.Circle(static, ob["r"], (ob["x"], ob["y"]))
                shape.friction = 0.9
                shape.filter = WORLD_FILTER
                self.space.add(shape)
            elif kind == "block":
                x, y, w, h = ob["x"], ob["y"], ob["w"], ob["h"]
                if ob["kind"] == "plank":
                    verts = [(x - w / 2, y - h / 2), (x + w / 2, y - h / 2),
                             (x + w / 2, y + h / 2), (x - w / 2, y + h / 2)]
                else:
                    # a box with sloped sides, so the bike can drive up and over
                    s = h * 1.35
                    verts = [(x - w / 2 - s, y + h / 2), (x - w / 2, y - h / 2),
                             (x + w / 2, y - h / 2), (x + w / 2 + s, y + h / 2)]
                shape = pymunk.Poly(static, verts, radius=1.5)
                shape.friction = 0.9
                shape.filter = WORLD_FILTER
                self.space.add(shape)
            elif kind == "crates":
                for col in range(ob["cols"]):
                    for row in range(ob["rows"]):
                        body = pymunk.Body(0.9, pymunk.moment_for_box(0.9, (CRATE, CRATE)))
                        body.position = (ob["x"] + col * (CRATE + 1),
                                         ob["y"] - CRATE / 2 - row * (CRATE + 1))
                        shape = pymunk.Poly.create_box(body, (CRATE, CRATE), radius=1)
                        shape.friction = 0.7
                        shape.filter = WORLD_FILTER
                        self.space.add(body, shape)
                        self.crates.append((body, shape))
                        self.crate_start.append((body, Vec2d(*body.position), 0.0))

    def reset_crates(self):
        """Put every crate back in its starting place (used after a crash)."""
        for body, pos, angle in self.crate_start:
            body.position = pos
            body.angle = angle
            body.velocity = (0, 0)
            body.angular_velocity = 0
            body.activate()

    # ----- ragdoll (the rider flying off after a crash) -----
    def add_ragdoll(self, pos, vel):
        self.remove_ragdoll()
        body = pymunk.Body(3.0, pymunk.moment_for_circle(3.0, 0, 22))
        body.position = pos
        body.velocity = vel
        body.angular_velocity = 6.0
        shape = pymunk.Circle(body, 22)
        shape.friction = 0.9
        shape.elasticity = 0.3
        shape.filter = pymunk.ShapeFilter(categories=CAT_BIKE, mask=CAT_WORLD, group=2)
        self.space.add(body, shape)
        self.ragdoll = (body, shape)

    def remove_ragdoll(self):
        if self.ragdoll:
            self.space.remove(*self.ragdoll)
            self.ragdoll = None

    # ----- stepping -----
    def step(self, dt, bike=None):
        sub = dt / SUBSTEPS
        for _ in range(SUBSTEPS):
            if bike:
                bike.apply_forces(sub)
            self.space.step(sub)


class Bike:
    """A dirt bike: frame + two wheels on suspension + engine motor."""

    R = 30                   # wheel radius
    HB = 76                  # half the wheelbase
    REST = 46                # suspension rest length
    ANCHOR_Y = 2
    TRAVEL = 56
    # rider points used for crash detection: (x, y, radius) in frame space
    RIDER = ((4, -112, 17), (-16, -64, 19), (-30, -38, 17))

    def __init__(self, world, spec, pos, angle=0.0):
        self.world = world
        self.space = world.space
        self.spec = spec
        self.phys = physics_for(spec)
        self.lean_cmd = 0.0
        self.parts = []

        mass = 10.0
        moment = pymunk.moment_for_box(mass, (170, 120)) * 1.5
        self.frame = pymunk.Body(mass, moment)
        self.frame.position = pos
        self.frame.angle = angle
        body_shape = pymunk.Poly.create_box(self.frame, (150, 26), radius=2)
        body_shape.friction = 0.5
        body_shape.filter = BIKE_FILTER
        self.space.add(self.frame, body_shape)
        self.parts += [self.frame, body_shape]

        self.wheels = []
        for side in (-1, 1):
            anchor_x = side * self.HB
            wheel = pymunk.Body(2.0, pymunk.moment_for_circle(2.0, 0, self.R))
            wheel.position = self.frame.local_to_world((anchor_x, self.ANCHOR_Y + self.REST))
            shape = pymunk.Circle(wheel, self.R)
            shape.friction = self.phys["friction"]
            shape.elasticity = 0.05
            shape.filter = BIKE_FILTER
            groove = pymunk.GrooveJoint(
                self.frame, wheel,
                (anchor_x, self.ANCHOR_Y + 6),
                (anchor_x, self.ANCHOR_Y + 6 + self.TRAVEL), (0, 0))
            spring = pymunk.DampedSpring(
                self.frame, wheel, (anchor_x, self.ANCHOR_Y), (0, 0),
                self.REST, 6500, 330)
            self.space.add(wheel, shape, groove, spring)
            self.parts += [wheel, shape, groove, spring]
            self.wheels.append(wheel)
        self.rear, self.front = self.wheels

        self.motor = pymunk.SimpleMotor(self.frame, self.rear, 0.0)
        self.motor.max_force = 0
        self.front_brake = pymunk.SimpleMotor(self.frame, self.front, 0.0)
        self.front_brake.max_force = 0
        self.space.add(self.motor, self.front_brake)
        self.parts += [self.motor, self.front_brake]

    # ----- controls -----
    def set_controls(self, throttle, brake, lean):
        p = self.phys
        forward = Vec2d(1, 0).rotated(self.frame.angle)
        speed = self.frame.velocity.dot(forward)
        self.lean_cmd = max(-1.0, min(1.0, lean))
        self.front_brake.max_force = 0
        if brake:
            if speed < 30 and not throttle:                      # reverse
                self.motor.rate = 9.0
                self.motor.max_force = p["engine_force"] * 0.5
            else:                                               # brake
                self.motor.rate = 0.0
                self.motor.max_force = 700_000
                self.front_brake.rate = 0.0
                self.front_brake.max_force = 500_000
        elif throttle:
            self.motor.rate = -p["top_rate"]
            self.motor.max_force = p["engine_force"]
        else:
            self.motor.rate = 0.0
            self.motor.max_force = 6000                         # engine braking

    def apply_forces(self, dt):
        f = self.frame
        f.torque = self.lean_cmd * self.phys["lean"]
        # a little rotation damping so the bike does not spin forever
        f.angular_velocity *= (1.0 - 0.35 * dt)
        if f.angular_velocity > 9.0:
            f.angular_velocity = 9.0
        elif f.angular_velocity < -9.0:
            f.angular_velocity = -9.0

    # ----- information -----
    @property
    def position(self):
        return self.frame.position

    @property
    def speed(self):
        return self.frame.velocity.length

    def wheel_on_ground(self, wheel):
        hit = self.space.point_query_nearest(wheel.position, self.R + 4, QUERY_FILTER)
        return hit is not None

    def rear_local(self):
        return self.frame.world_to_local(self.rear.position)

    def front_local(self):
        return self.frame.world_to_local(self.front.position)

    def rider_world(self, index=0):
        lx, ly, _ = self.RIDER[index]
        return self.frame.local_to_world((lx, ly))

    def crashed(self):
        for lx, ly, r in self.RIDER:
            p = self.frame.local_to_world((lx, ly))
            if self.space.point_query_nearest(p, r, QUERY_FILTER) is not None:
                return True
        return False

    def remove(self):
        for part in self.parts:
            try:
                self.space.remove(part)
            except Exception:
                pass
        self.parts = []
