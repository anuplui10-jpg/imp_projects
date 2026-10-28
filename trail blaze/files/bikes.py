# bikes.py
# The bikes you can buy with gold. Stats are 1-10 and shown on the Bike screen.
# physics_for() turns the stats into the real numbers used by the physics engine.

BIKES = [
    {
        "id": "rookie", "name": "ROOKIE 125", "price": 0,
        "color": (70, 205, 95), "dark": (28, 120, 55),
        "power": 4, "speed": 4, "grip": 5, "control": 5,
        "blurb": "A friendly starter bike. Easy to learn.",
    },
    {
        "id": "hawk", "name": "DIRT HAWK 250", "price": 300,
        "color": (255, 150, 35), "dark": (170, 80, 10),
        "power": 6, "speed": 6, "grip": 6, "control": 6,
        "blurb": "More power and better grip for steep hills.",
    },
    {
        "id": "pro", "name": "PRO TRIALS 300", "price": 800,
        "color": (65, 145, 255), "dark": (25, 75, 170),
        "power": 8, "speed": 7, "grip": 8, "control": 8,
        "blurb": "A pro bike. Sticks to the ground and turns fast in the air.",
    },
    {
        "id": "inferno", "name": "INFERNO X", "price": 1800,
        "color": (240, 55, 55), "dark": (120, 15, 20),
        "power": 10, "speed": 9, "grip": 9, "control": 10,
        "blurb": "The fastest and strongest bike in the game.",
    },
]


def bike_by_id(bike_id):
    for bike in BIKES:
        if bike["id"] == bike_id:
            return bike
    return BIKES[0]


def physics_for(bike):
    """Turn the 1-10 stats into numbers for the physics engine."""
    return {
        "engine_force": 300_000 + 80_000 * bike["power"],   # wheel torque
        "top_rate": 18.0 + 1.6 * bike["speed"],              # max wheel spin (rad/s)
        "friction": 1.2 + 0.1 * bike["grip"],                # tire grip
        "lean": 200_000 + 40_000 * bike["control"],          # lean torque
    }
