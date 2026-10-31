TRIAL BLAZE - HD off-road trials bike game (Python, pygame-ce + pymunk)

HOW TO RUN
  1. pip install -r requirements.txt        (or: pip install pygame-ce pymunk)
  2. python trial_blaze.py

CONTROLS
  UP / W      gas
  DOWN / S    brake (then reverse)
  LEFT / A    lean back (nose up)
  RIGHT / D   lean forward (nose down)
  R           restart from the last checkpoint
  ESC         pause / go back
  F11         full screen
  M           sound on / off

FILES
  trial_blaze.py   the game: menus, bike shop, about screen, gameplay, HUD
  art.py           all drawing code (backgrounds, ground, bikes, buttons)
  sounds.py        engine sound, effects and music (made by code, no files)
  physics.py       the bike and the world (pymunk physics)
  levels.py        the 7 levels (easy to edit)
  bikes.py         the bikes, prices and stats
  save.json        created automatically (gold, bikes, stars, best times)
                   delete it to reset your progress

EDITING
  Levels: open levels.py. Each level is a few lines like b.flat(900),
  b.ramp(260, 85), b.gap(190, -45), b.log(200, 24), b.coin_line(...).
  Bikes: open bikes.py and change price or the 1-10 stats.

NOTE FOR NEW PYTHON VERSIONS (3.14)
  The classic "pygame" package has no install file for Python 3.14, so pip
  tries to build it and fails. Use "pygame-ce" instead. It is the same
  library: the game still does "import pygame".
  If you get odd errors, run:  pip uninstall pygame pygame-ce
  and then:                    pip install pygame-ce pymunk

STUNTS (extra gold, added when you finish the level)
  WHEELIE      keep the front wheel up for 1+ seconds
  AIR TIME     a jump of about half a second or more (+10), BIG AIR (+30), HUGE AIR (+60)
  BACKFLIP / FRONTFLIP   one full turn in the air, then land safely (+50 each)
  Tip: the big cliff jump at the end of level 4 is the best place for a backflip.

GHOST
  Finish a level with 0 faults and your run is saved as a see-through "ghost"
  bike. Next time you play that level you race against it.

SOUND
  Music is a quiet generated loop. Press M to mute everything, or set
  MUSIC = False at the top of sounds.py to remove only the music.
