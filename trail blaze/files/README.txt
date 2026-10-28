TRIAL BLAZE - HD off-road trials bike game (Python, pygame + pymunk)

HOW TO RUN
  1. pip install -r requirements.txt        (or: pip install pygame pymunk)
  2. python trial_blaze.py

CONTROLS
  UP / W      gas
  DOWN / S    brake (then reverse)
  LEFT / A    lean back (nose up)
  RIGHT / D   lean forward (nose down)
  R           restart from the last checkpoint
  ESC         pause / go back
  F11         full screen

FILES
  trial_blaze.py   the game: menus, bike shop, about screen, gameplay, HUD
  art.py           all drawing code (backgrounds, ground, bikes, buttons)
  physics.py       the bike and the world (pymunk physics)
  levels.py        the 7 levels (easy to edit)
  bikes.py         the bikes, prices and stats
  save.json        created automatically (gold, bikes, stars, best times)
                   delete it to reset your progress

EDITING
  Levels: open levels.py. Each level is a few lines like b.flat(900),
  b.ramp(260, 85), b.gap(190, -45), b.log(200, 24), b.coin_line(...).
  Bikes: open bikes.py and change price or the 1-10 stats.
