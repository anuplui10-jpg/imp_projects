from ursina import *
from ursina.shaders import lit_with_shadows_shader, unlit_shader
from ursina.shaders.unlit_with_fog_shader import unlit_with_fog_shader
from math import sin, cos, radians, degrees, asin, atan2, sqrt, pi
from pathlib import Path
import random, wave, struct

# =====================================================================
#  ANIME RUN   (Ursina)
#  A / D or LEFT / RIGHT : change lane, and TURN at corners
#  SPACE / W / UP        : jump
#  S / DOWN              : slide (duck under branches and vines)
#  R                     : restart      ESC : quit
# =====================================================================

# =====================================================================
#  1. SOUNDS - the game makes its own sound files the first time it runs
# =====================================================================
HERE = Path(__file__).resolve().parent
SND = HERE / 'jungle_sounds'
RATE = 22050


def _save(name, data):
    peak = max(0.001, max(abs(x) for x in data))
    pcm = b''.join(struct.pack('<h', int(x / peak * 0.9 * 32767)) for x in data)
    with wave.open(str(SND / name), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm)


def _noise(n, lp):
    """random noise; a small lp makes it deeper (like rumble)"""
    y, out = 0.0, []
    for _ in range(n):
        y += lp * (random.uniform(-1, 1) - y)
        out.append(y)
    return out


def _fade_ends(data, secs=0.4):
    k = int(RATE * secs)
    for i in range(k):
        data[i] *= i / k
        data[-1 - i] *= i / k
    return data


def make_sounds():
    if (SND / 'ready_v2.txt').exists():
        return
    SND.mkdir(exist_ok=True)
    R = RATE
    # footsteps on dirt (two versions so it does not sound robotic)
    for nm in ('step_a', 'step_b'):
        n = int(R * 0.13)
        nz = _noise(n, random.uniform(0.18, 0.3))
        f = random.uniform(80, 110)
        _save(nm + '.wav', [(nz[i] * 3 + 0.8 * sin(2 * pi * f * i / R)) * (1 - i / n) ** 4 for i in range(n)])
    # jump whoosh
    n = int(R * 0.3)
    nz = _noise(n, 0.5)
    ph, d = 0.0, []
    for i in range(n):
        ph += 2 * pi * (250 + 450 * i / n) / R
        d.append((0.4 * sin(ph) + nz[i] * 1.5) * sin(pi * i / n))
    _save('jump.wav', d)
    # landing thud
    n = int(R * 0.22)
    nz = _noise(n, 0.15)
    _save('land.wav', [(sin(2 * pi * 65 * i / R) + nz[i] * 3) * (1 - i / n) ** 3 for i in range(n)])
    # coin ding
    n = int(R * 0.4)
    d = []
    for i in range(n):
        t = i / R
        if t < 0.09:
            d.append(sin(2 * pi * 988 * t) * 2.718 ** (-t * 10))
        else:
            d.append(sin(2 * pi * 1319 * (t - 0.09)) * 2.718 ** (-(t - 0.09) * 7))
    _save('coin.wav', d)
    # hit / crash
    n = int(R * 0.6)
    nz = _noise(n, 0.3)
    _save('hit.wav', [(nz[i] * 3 + sin(2 * pi * 55 * i / R)) * (1 - i / n) ** 2.5 for i in range(n)])
    # tree / pillar collapse (long rumble + cracks + crash)
    n = int(R * 2.2)
    rumble = _noise(n, 0.035)
    d = [rumble[i] * 14 * sin(pi * i / n) ** 0.7 for i in range(n)]
    for _ in range(16):
        st0 = random.randint(int(n * 0.1), int(n * 0.9))
        ln = int(R * 0.08)
        bn = _noise(ln, 0.5)
        for j in range(ln):
            if st0 + j < n:
                d[st0 + j] += bn[j] * 1.2 * (1 - j / ln) ** 2
    cn = int(R * 0.6)
    bn = _noise(cn, 0.25)
    for j in range(cn):
        k = int(n * 0.55) + j
        if k < n:
            d[k] += bn[j] * 4 * (1 - j / cn) ** 2
    _save('collapse.wav', d)
    # bear roar
    n = int(R * 1.5)
    nz = _noise(n, 0.35)
    ph, d = 0.0, []
    for i in range(n):
        t = i / R
        ph += 2 * pi * (62 + 12 * sin(2 * pi * 4 * t)) / R
        saw = ((ph / (2 * pi)) % 1) * 2 - 1
        am = 0.55 + 0.45 * sin(2 * pi * 26 * t)
        d.append((saw * 0.7 + nz[i] * 0.8) * am * sin(pi * i / n) ** 0.5)
    _save('roar.wav', d)
    # bear heavy footstep
    n = int(R * 0.25)
    nz = _noise(n, 0.12)
    _save('bear_step.wav', [(nz[i] * 6 + sin(2 * pi * 48 * i / R)) * (1 - i / n) ** 3 for i in range(n)])
    # jungle ambience (wind + birds)
    n = int(R * 8)
    wind = _noise(n, 0.02)
    d = [wind[i] * 12 * (0.6 + 0.4 * sin(2 * pi * i / n * 2)) for i in range(n)]
    for _ in range(7):
        st0 = random.randint(0, n - int(R * 1.2))
        f0 = random.uniform(2200, 3600)
        for note in range(random.randint(2, 4)):
            ln = int(R * 0.09)
            base = st0 + note * int(R * 0.13)
            for j in range(ln):
                if base + j < n:
                    d[base + j] += 0.22 * sin(2 * pi * (f0 + 600 * j / ln) * j / R) * sin(pi * j / ln)
    _save('ambient.wav', _fade_ends(d))
    # river water
    n = int(R * 4)
    a, b = _noise(n, 0.25), _noise(n, 0.08)
    d = [(a[i] * 2 + b[i] * 4) * (0.7 + 0.3 * sin(2 * pi * i / R * 3.1)) for i in range(n)]
    _save('river.wav', _fade_ends(d))
    (SND / 'ready_v2.txt').write_text('ok')


# =====================================================================
#  2. WINDOW, UI (made first so they stay simple), LIGHT, FOG
# =====================================================================
app = Ursina(title='Anime Run', borderless=False)

SKY = (0.66, 0.82, 0.80)
window.color = color.rgb(*SKY)
window.fps_counter.enabled = False
window.entity_counter.enabled = False
window.collider_counter.enabled = False
window.exit_button.visible = False
scene.fog_color = color.rgb(*SKY)
scene.fog_density = (30, 125)
camera.clip_plane_far = 400
camera.fov = 80
Sky(texture='sky_default')

# =====================================================================
#  LOADING SCREEN (this shows first, while the game builds itself)
# =====================================================================
MODE = 'loading'                      # 'loading' -> 'menu' -> 'skins' or 'play'
PINK = color.rgb(1.0, 0.35, 0.65)
CYAN = color.rgb(0.2, 0.85, 1.0)

loading_ui = Entity(parent=camera.ui)
Entity(parent=loading_ui, model='quad', scale=(3, 3), color=color.rgb(0.04, 0.03, 0.12), z=5, shader=None)
Entity(parent=loading_ui, model='quad', scale=(3, 0.9), y=-0.55, color=color.rgba(0.35, 0.05, 0.4, 0.55), z=4, shader=None)
for _ in range(14):                   # anime speed lines
    Entity(parent=loading_ui, model='quad', scale=(random.uniform(0.4, 1.2), 0.004),
           x=random.uniform(-0.9, 0.9), y=random.uniform(-0.5, 0.5),
           color=color.rgba(1, 1, 1, random.uniform(0.08, 0.25)), z=3, shader=None)
Text('ANIME RUN', parent=loading_ui, origin=(0, 0), scale=5, position=(0.008, 0.112), color=CYAN)
Text('ANIME RUN', parent=loading_ui, origin=(0, 0), scale=5, position=(0, 0.12), color=PINK)
Text('RUN  -  DODGE  -  ESCAPE', parent=loading_ui, origin=(0, 0), scale=1.3, position=(0, 0.03),
     color=color.rgba(1, 1, 1, 0.7))
Entity(parent=loading_ui, model='quad', scale=(0.62, 0.034), y=-0.1, color=color.rgba(1, 1, 1, 0.15), z=2, shader=None)
load_fill = Entity(parent=loading_ui, model='quad', origin=(-0.5, 0), x=-0.3, y=-0.1, scale=(0.0, 0.026),
                   color=PINK, z=1, shader=None)
load_text = Text('Loading...', parent=loading_ui, origin=(0, 0), scale=1.2, position=(0, -0.16), color=color.white)
Text('TIP: press S to slide under low branches', parent=loading_ui, origin=(0, 0), scale=1.0,
     position=(0, -0.4), color=color.rgba(1, 1, 1, 0.6))


def load_step(p, msg):
    """move the loading bar and draw one frame so you can see it"""
    load_fill.scale_x = 0.6 * p
    load_text.text = f'{msg}...  {int(p * 100)}%'
    app.step()


load_step(0.05, 'Starting')
make_sounds()
load_step(0.3, 'Sounds ready')

# ----- UI -----
score_text = Text(text='', position=(-0.86, 0.47), scale=1.6, color=color.white)
coin_text = Text(text='', position=(-0.86, 0.42), scale=1.3, color=color.gold)
turn_text = Text(text='', origin=(0, 0), y=0.28, scale=2.2, color=color.yellow)
center_text = Text(text='', origin=(0, 0), y=0.05, scale=1.8, color=color.white)
danger_bg = Entity(parent=camera.ui, model='quad', color=color.rgba(0, 0, 0, 0.5),
                   scale=(0.3, 0.022), position=(0.55, 0.47), shader=None)
danger_fill = Entity(parent=camera.ui, model='quad', color=color.red, origin=(-0.5, 0),
                     position=(0.4, 0.47), scale=(0.0, 0.016), z=-0.01, shader=None)
danger_label = Text(text='BEAR', position=(0.33, 0.495), scale=1.0, color=color.white)
flash = Entity(parent=camera.ui, model='quad', scale=(3, 3), color=color.rgba(1, 0, 0, 0), z=-2, shader=None)
overlay = Entity(parent=camera.ui, model='quad', scale=(3, 3), color=color.rgba(0, 0, 0, 0.55), z=1, shader=None,
                 enabled=False)


# =====================================================================
#  SKIN LOOKS  (colors are (red, green, blue) from 0 to 1)
#  To make a NEW skin: copy one block, change the name, colors and extras.
#  hair_style: 'short' 'spiky' 'long' 'twintail'
#  runner extras: headband scarf mask katana katana_hip cape wristbands skirt visor shoulders glow
#  chaser extras: horns spikes ice fox_ears tails panda wisps
# =====================================================================
RUNNER_LOOKS = [
    dict(name='Explorer', skin=(0.88, 0.69, 0.53), shirt=(0.82, 0.42, 0.18), pants=(0.2, 0.24, 0.36),
         shoe=(0.12, 0.1, 0.1), hair=(0.1, 0.07, 0.05), hair_style='short', eye=(0.05, 0.04, 0.04),
         hat=(0.45, 0.3, 0.15), pack=(0.55, 0.4, 0.22), accent=(0.9, 0.8, 0.3), extras=[]),
    dict(name='Ninja', skin=(0.88, 0.69, 0.53), shirt=(0.12, 0.12, 0.2), pants=(0.1, 0.1, 0.16),
         shoe=(0.05, 0.05, 0.08), hair=(0.05, 0.05, 0.09), hair_style='spiky', eye=(0.9, 0.9, 0.95),
         hat=None, pack=None, accent=(0.85, 0.1, 0.15), extras=['headband', 'scarf', 'mask', 'katana']),
    dict(name='Blaze', skin=(0.9, 0.72, 0.56), shirt=(0.95, 0.95, 0.95), pants=(0.1, 0.1, 0.13),
         shoe=(0.85, 0.15, 0.1), hair=(0.92, 0.2, 0.08), hair_style='spiky', eye=(0.05, 0.04, 0.04),
         hat=None, pack=None, accent=(1.0, 0.5, 0.1), extras=['headband', 'wristbands']),
    dict(name='Spirit', skin=(0.93, 0.8, 0.7), shirt=(0.15, 0.2, 0.42), pants=(0.12, 0.12, 0.22),
         shoe=(0.08, 0.08, 0.12), hair=(0.93, 0.95, 1.0), hair_style='long', eye=(0.2, 0.85, 0.95),
         hat=None, pack=None, accent=(0.3, 0.85, 0.95), extras=['cape', 'katana_hip']),
    dict(name='Idol', skin=(0.95, 0.8, 0.7), shirt=(1.0, 0.6, 0.8), pants=(1.0, 0.85, 0.9),
         shoe=(0.95, 0.95, 1.0), hair=(1.0, 0.45, 0.7), hair_style='twintail', eye=(0.25, 0.5, 1.0),
         hat=None, pack=None, accent=(1.0, 0.95, 0.5), extras=['skirt']),
    dict(name='Cyber', skin=(0.85, 0.7, 0.58), shirt=(0.1, 0.12, 0.22), pants=(0.09, 0.09, 0.17),
         shoe=(0.1, 0.1, 0.15), hair=(0.8, 0.92, 1.0), hair_style='spiky', eye=(0.2, 0.9, 1.0),
         hat=None, pack=None, accent=(0.2, 0.9, 1.0), extras=['visor', 'shoulders', 'glow']),
]

CHASER_LOOKS = [
    dict(name='Bear', fur=(0.30, 0.18, 0.10), paw=(0.18, 0.1, 0.06), light=(0.58, 0.42, 0.28),
         eye=(1.0, 0.25, 0.1), accent=(0.3, 0.18, 0.1), extras=[]),
    dict(name='Oni', fur=(0.62, 0.1, 0.1), paw=(0.2, 0.05, 0.05), light=(0.85, 0.55, 0.45),
         eye=(1.0, 0.9, 0.2), accent=(0.95, 0.92, 0.8), extras=['horns', 'spikes']),
    dict(name='Frost', fur=(0.85, 0.93, 1.0), paw=(0.5, 0.7, 0.9), light=(0.97, 0.99, 1.0),
         eye=(0.2, 0.8, 1.0), accent=(0.6, 0.9, 1.0), extras=['ice']),
    dict(name='Kitsune', fur=(0.95, 0.55, 0.15), paw=(0.25, 0.12, 0.06), light=(1.0, 0.95, 0.85),
         eye=(0.9, 0.2, 0.9), accent=(1.0, 0.97, 0.9), extras=['fox_ears', 'tails']),
    dict(name='Panda', fur=(0.96, 0.96, 0.96), paw=(0.08, 0.08, 0.08), light=(0.96, 0.96, 0.96),
         eye=(0.9, 0.1, 0.1), accent=(0.08, 0.08, 0.08), extras=['panda']),
    dict(name='Shadow', fur=(0.1, 0.08, 0.16), paw=(0.05, 0.03, 0.08), light=(0.2, 0.15, 0.3),
         eye=(0.75, 0.25, 1.0), accent=(0.6, 0.2, 1.0), extras=['wisps']),
]


# =====================================================================
#  MAIN MENU + SKINS SCREEN (made now, shown after loading)
# =====================================================================
SKINS = {                              # (name, unlocked?)  - made from the looks above
    'runner': [(l['name'], True) for l in RUNNER_LOOKS],
    'chaser': [(l['name'], True) for l in CHASER_LOOKS],
}
selected_skin = {'runner': 0, 'chaser': 0}
skin_cards = {}

menu_ui = Entity(parent=camera.ui, enabled=False)
Entity(parent=menu_ui, model='quad', scale=(0.64, 1.3), x=-0.55, color=color.rgba(0.03, 0.02, 0.12, 0.6), z=2, shader=None)
Text('ANIME', parent=menu_ui, position=(-0.83, 0.4), scale=5, color=PINK)
Text('RUN', parent=menu_ui, position=(-0.83, 0.28), scale=5, color=CYAN)
Text('RUN  -  DODGE  -  ESCAPE', parent=menu_ui, position=(-0.83, 0.15), scale=1.0, color=color.rgba(1, 1, 1, 0.7))
btn_play = Button(parent=menu_ui, text='PLAY', scale=(0.4, 0.1), position=(-0.55, 0.0), z=1,
                  color=color.rgb(0.95, 0.25, 0.5), highlight_color=color.rgb(1, 0.45, 0.65),
                  pressed_color=color.rgb(0.7, 0.15, 0.4))
btn_skins = Button(parent=menu_ui, text='SKINS', scale=(0.4, 0.1), position=(-0.55, -0.13), z=1,
                   color=color.rgb(0.15, 0.6, 0.9), highlight_color=color.rgb(0.35, 0.78, 1),
                   pressed_color=color.rgb(0.1, 0.45, 0.7))
btn_quit = Button(parent=menu_ui, text='QUIT', scale=(0.4, 0.08), position=(-0.55, -0.26), z=1,
                  color=color.rgb(0.3, 0.25, 0.4), highlight_color=color.rgb(0.45, 0.4, 0.6))
best_text = Text('', parent=menu_ui, position=(-0.83, -0.38), scale=1.2, color=color.gold)
Text('A / D  move     SPACE  jump     S  slide', parent=menu_ui, position=(-0.85, -0.44), scale=0.9,
     color=color.rgba(1, 1, 1, 0.6))

skins_ui = Entity(parent=camera.ui, enabled=False)
Entity(parent=skins_ui, model='quad', scale=(1.62, 0.7), y=-0.2, color=color.rgba(0.03, 0.02, 0.12, 0.8), z=2, shader=None)
Text('SKINS', parent=skins_ui, origin=(0, 0), position=(0, 0.44), scale=3.5, color=PINK)
for kind, label, y in (('runner', 'RUNNER', -0.02), ('chaser', 'CHASER', -0.27)):
    Text(label, parent=skins_ui, position=(-0.78, y + 0.15), scale=1.4, color=CYAN)
    n = len(SKINS[kind])
    for i in range(n):
        skin_cards[(kind, i)] = Button(parent=skins_ui, scale=(0.22, 0.14), position=(-(n - 1) * 0.1175 + i * 0.235, y), z=1,
                                       on_click=lambda k=kind, m=i: select_skin(k, m))
btn_back = Button(parent=skins_ui, text='BACK', scale=(0.3, 0.07), position=(0, -0.48), z=1,
                  color=color.rgb(0.95, 0.25, 0.5), highlight_color=color.rgb(1, 0.45, 0.65))


def refresh_skins():
    for (kind, i), b in skin_cards.items():
        name, unlocked = SKINS[kind][i]
        if not unlocked:
            b.color, b.highlight_color, b.text = color.rgb(0.2, 0.2, 0.26), color.rgb(0.2, 0.2, 0.26), f'{name}\nLOCKED'
        elif selected_skin[kind] == i:
            b.color, b.highlight_color, b.text = color.rgb(0.15, 0.65, 0.35), color.rgb(0.25, 0.8, 0.45), f'{name}\nSELECTED'
        else:
            b.color, b.highlight_color, b.text = color.rgb(0.15, 0.45, 0.8), color.rgb(0.3, 0.6, 0.95), f'{name}\nSelect'


def apply_skins():
    """build the runner and the chaser again with the skins that were picked"""
    global player, bear
    p_pos, p_yaw, b_pos = player.position, player.rotation_y, bear.position
    kill(player)
    kill(bear)
    player = Human(RUNNER_LOOKS[selected_skin['runner']])
    bear = Bear(CHASER_LOOKS[selected_skin['chaser']])
    player.position, player.rotation_y, bear.position = p_pos, p_yaw, b_pos
    player.pose(0, 0, False, False, 0)
    bear.gallop(0)


def select_skin(kind, i):
    if SKINS[kind][i][1]:
        selected_skin[kind] = i
        refresh_skins()
        apply_skins()


def set_hud(on):
    for e in (score_text, coin_text, turn_text, center_text, danger_bg, danger_fill, danger_label):
        e.enabled = on


def show_menu(rebuild=True):
    global MODE
    if rebuild:
        new_run(menu=True)
    MODE = 'menu'
    loading_ui.enabled = False
    skins_ui.enabled = False
    menu_ui.enabled = True
    overlay.enabled = False
    set_hud(False)
    best_text.text = f'BEST: {st.best}'
    mouse.visible = True


def show_skins():
    global MODE
    MODE = 'skins'
    menu_ui.enabled = False
    skins_ui.enabled = True
    refresh_skins()


def start_game():
    global MODE
    if not st.menu_ready:
        new_run(menu=True)
    MODE = 'play'
    menu_ui.enabled = False
    skins_ui.enabled = False
    set_hud(True)
    mouse.visible = False
    begin_run()


btn_play.on_click = start_game
btn_skins.on_click = show_skins
btn_quit.on_click = application.quit
btn_back.on_click = lambda: show_menu(rebuild=False)
set_hud(False)                         # the score / bear bar only show while playing


# ----- light -----
Entity.default_shader = lit_with_shadows_shader
AmbientLight(color=color.rgba(0.55, 0.5, 0.5, 1))
sun = DirectionalLight(shadow_map_resolution=Vec2(2048, 2048), shadows=True, color=color.rgb(1.0, 0.92, 0.78))
sun.rotation = Vec3(50, -25, 0)
_lens = sun._light.get_lens()
_lens.set_near_far(-80, 80)
_lens.set_film_size(60, 90)
_lens.set_film_offset(0, 0)
load_step(0.45, 'Lighting')

# ----- sounds -----


def load_sound(name, vol=1.0, loop=False):
    try:
        return Audio(SND / name, autoplay=False, loop=loop, volume=vol)
    except Exception as e:
        print('sound problem:', name, e)
        return None


s_steps = [load_sound('step_a.wav', 0.5), load_sound('step_b.wav', 0.5)]
s_jump = load_sound('jump.wav', 0.5)
s_land = load_sound('land.wav', 0.6)
s_coin = load_sound('coin.wav', 0.5)
s_hit = load_sound('hit.wav', 0.9)
s_collapse = load_sound('collapse.wav', 1.0)
s_roar = load_sound('roar.wav', 1.0)
s_bear = load_sound('bear_step.wav', 0.8)
s_amb = load_sound('ambient.wav', 0.5, loop=True)
s_river = load_sound('river.wav', 0.0, loop=True)
load_step(0.6, 'Loading sounds')


def play(a, vol=1.0, pitch=1.0):
    if a:
        a.volume = vol
        a.pitch = pitch
        a.play()


# =====================================================================
#  3. SMALL HELPERS
# =====================================================================
W = 7.0                       # path width
LANES = [-2.3, 0.0, 2.3]
DIRS = [Vec3(0, 0, 1), Vec3(1, 0, 0), Vec3(0, 0, -1), Vec3(-1, 0, 0)]
CAVE_LEN = 44
MIN_OBSTACLE_DIST = 48        # first obstacle is ~5 seconds after the start
START_GAP = 9.0
CAUGHT_GAP = 2.2
START_CUM = 31.0              # the runner starts 6 units into the cave


def fwd(h):
    return DIRS[h % 4]


def rgt(h):
    d = DIRS[h % 4]
    return Vec3(d.z, 0, -d.x)


def dot(a, b):
    return a.x * b.x + a.y * b.y + a.z * b.z


def C(t, j=0.0):
    if j:
        return color.rgb(*[max(0, min(1, v + random.uniform(-j, j))) for v in t])
    return color.rgb(*t)


def box(parent, x, y, z, sx, sy, sz, c, **kw):
    return Entity(parent=parent, model='cube', position=(x, y, z), scale=(sx, sy, sz), color=c, **kw)


def ball(parent, x, y, z, sx, sy, sz, c, model='icosphere', **kw):
    return Entity(parent=parent, model=model, position=(x, y, z), scale=(sx, sy, sz), color=c, **kw)


class Obj:
    pass


def kill(e):
    """destroy an entity AND everything attached to it (Ursina's destroy leaves the children behind)"""
    for ch in list(e.children):
        kill(ch)
    destroy(e)


st = Obj()
GREENS = [(0.10, 0.36, 0.14), (0.16, 0.46, 0.16), (0.08, 0.30, 0.18), (0.24, 0.52, 0.18)]
BROWN = (0.33, 0.22, 0.13)
ROCK = [(0.45, 0.42, 0.38), (0.52, 0.47, 0.40), (0.38, 0.36, 0.34)]

# =====================================================================
#  4. DECORATION: trees, vines, ropes, rocks, pillars
# =====================================================================


def vine(p, x, ytop, z, length):
    box(p, x, ytop - length / 2, z, 0.07, length, 0.07, C((0.15, 0.42, 0.15), 0.05))
    ball(p, x, ytop - length, z, 0.35, 0.5, 0.35, C((0.2, 0.55, 0.2), 0.05))


def tree(p, x, z, big=False):
    # Reject trees whose branches could enter the racing track
    max_tree_width = 3.8 * 1.3 / 2 + 1.3
    safe_distance = W / 2 + 0.5

    if abs(x) - max_tree_width <= safe_distance:
        return

    h = random.uniform(8, 14) if big else random.uniform(5, 9)
    tw = random.uniform(0.55, 0.9) * (1.5 if big else 1)

    box(p, x, h / 2, z, tw, h, tw, C(BROWN, 0.04))

    if big:
        for ang in (0, 90):
            box(p, x, 0.6, z, tw * 2.4, 1.2,
                tw * 0.5, C(BROWN, 0.04)).rotation_y = ang + random.uniform(-15, 15)

    for _ in range(3 if big else 2):
        s = random.uniform(2.4, 3.8) * (1.3 if big else 1)
        ball(p, x + random.uniform(-1.3, 1.3),
             h + random.uniform(-0.6, 1.2),
             z + random.uniform(-1.3, 1.3),
             s, s * 0.8, s, C(random.choice(GREENS), 0.04))

    if random.random() < 0.55:
        vine(p, x + random.uniform(-1.5, 1.5),
             h - 0.5, z + random.uniform(-1.5, 1.5),
             random.uniform(3, 6))


def bush(p, x, z):
    s = random.uniform(1.0, 1.8)
    ball(p, x, s * 0.35, z, s, s * 0.7, s, C(random.choice(GREENS), 0.05))
    if random.random() < 0.5:
        fc = random.choice([(0.9, 0.2, 0.25), (0.95, 0.85, 0.2), (0.9, 0.5, 0.8)])
        for _ in range(3):
            ball(p, x + random.uniform(-0.6, 0.6), s * 0.6 + random.uniform(0, 0.3), z + random.uniform(-0.6, 0.6),
                 0.22, 0.22, 0.22, C(fc))


def rock(p, x, z, size):
    r = ball(p, x, size * 0.35, z, size, size * 0.75, size * random.uniform(0.8, 1.2), C(random.choice(ROCK), 0.04))
    r.rotation_y = random.uniform(0, 360)


def rope_span(p, z, y):
    """a rope strung across the path high up, with hanging vines (the 'flying ropes')"""
    box(p, 0, y, z, W + 16, 0.09, 0.09, C((0.62, 0.5, 0.3)))
    for i in range(3):
        vine(p, random.uniform(-W / 2 - 2, W / 2 + 2), y, z, random.uniform(1.5, 3.5))


def cliff(p, side, z, tall=True):
    w = random.uniform(5, 9)
    h = random.uniform(8, 18) if tall else random.uniform(3, 7)
    x = side * (W / 2 + 1.8 + w / 2 + random.uniform(0, 3))
    box(p, x, h / 2, z, w, h, random.uniform(8, 12), C(random.choice(ROCK), 0.04))
    if random.random() < 0.6:
        box(p, x, h + 0.2, z, w * 0.9, 0.5, 8, C((0.2, 0.4, 0.16), 0.04))


def pillar(p, x, z, broken=False):
    h = random.uniform(1.5, 3) if broken else 5
    box(p, x, h / 2, z, 1.0, h, 1.0, C((0.55, 0.54, 0.48), 0.04))
    box(p, x, 0.2, z, 1.4, 0.4, 1.4, C((0.5, 0.49, 0.44), 0.03))
    if not broken:
        box(p, x, h + 0.2, z, 1.4, 0.4, 1.4, C((0.5, 0.49, 0.44), 0.03))
    ball(p, x, h * 0.5, z, 1.05, h * 0.6, 1.05, C((0.25, 0.45, 0.2), 0.03))   # moss


def decorate(sg):
    r, L, b = sg.root, sg.L, sg.biome
    d = Entity(parent=r)
    top = L - 6
    if b == 'cave':
        build_cave(sg, d)
    else:
        if b == 'jungle':
            for _ in range(int(L / 4.5)):
                side = random.choice((-1, 1))
                tree(d, side * (8.5 + random.random() ** 2 * 24), random.uniform(6, top), big=random.random() < 0.2)
            for _ in range(int(L / 3)):
                bush(d, random.choice((-1, 1)) * random.uniform(5.2, 9), random.uniform(6, top))
            for z in range(12, int(top), 22):
                ball(d, random.uniform(-3, 3), random.uniform(12, 14), z, 9, 2.2, 7, C(random.choice(GREENS), 0.04))
            for z in range(10, int(top), 14):
                vine(d, random.uniform(-3.4, 3.4), 11, z + random.uniform(-3, 3), random.uniform(3, 6))
            for z in range(20, int(top), 40):
                rope_span(d, z, random.uniform(8, 10))
        elif b == 'river':
            for z in range(4, int(top), 6):                                  # bridge posts and rope rails
                for side in (-1, 1):
                    box(d, side * (W / 2 - 0.15), 0.8, z, 0.25, 1.6, 0.25, C((0.4, 0.28, 0.16), 0.03))
            for side in (-1, 1):
                for y in (1.15, 0.6):
                    box(d, side * (W / 2 - 0.15), y, sg.total / 2, 0.08, 0.08, sg.total, C((0.66, 0.54, 0.32)))
            for _ in range(int(L / 4)):
                side = random.choice((-1, 1))
                tree(d, side * random.uniform(17, 45), random.uniform(6, top), big=random.random() < 0.3)
            for _ in range(int(L / 10)):
                rock(d, random.choice((-1, 1)) * random.uniform(14, 30), random.uniform(6, top), random.uniform(2, 4))
            for z in range(25, int(top), 45):
                rope_span(d, z, random.uniform(7, 9))
        elif b == 'rocks':
            for z in range(4, int(top), 8):
                cliff(d, -1, z)
                cliff(d, 1, z)
            for _ in range(int(L / 5)):
                rock(d, random.choice((-1, 1)) * random.uniform(6.4, 10), random.uniform(6, top), random.uniform(1.5, 3.2))
            for _ in range(int(L / 12)):
                side = random.choice((-1, 1))
                tree(d, side * random.uniform(14, 30), random.uniform(6, top))
        elif b == 'ruins':
            for z in range(8, int(top) - 22, 10):
                for side in (-1, 1):
                    pillar(d, side * (W / 2 + 1.2), z + random.uniform(-1, 1), broken=random.random() < 0.4)
            for z in range(30, int(top), 34):                                  # big arches
                for side in (-1, 1):
                    box(d, side * (W / 2 + 1.2), 3, z, 1.2, 6, 1.2, C((0.5, 0.49, 0.44), 0.03))
                box(d, 0, 6.3, z, W + 3.6, 1.0, 1.4, C((0.48, 0.47, 0.42), 0.03))
                ball(d, 0, 6.9, z, W, 0.8, 1.5, C((0.25, 0.45, 0.2)))
            for _ in range(int(L / 5)):
                tree(d, random.choice((-1, 1)) * random.uniform(11, 32), random.uniform(6, top), big=random.random() < 0.3)
            for _ in range(int(L / 6)):
                bush(d, random.choice((-1, 1)) * random.uniform(7, 12), random.uniform(6, top))
            for z in range(18, int(top), 40):
                rope_span(d, z, random.uniform(8, 10))
        if sg.turn:                                                              # wall at the end of a corner
            for i in range(9):
                ball(d, -6 + i * 1.5, 2 + random.uniform(0, 1.5), sg.total + 1.5, 3.2, 3.6, 3.2, C(random.choice(ROCK), 0.04))
            box(d, 0, 4.5, sg.total + 3.5, W + 16, 9, 3, C(ROCK[2]))
            tree(d, -(W / 2 + 4), sg.total - 3, big=True)
            tree(d, (W / 2 + 4), sg.total - 3, big=True)
    d.combine(include_normals=True)


def cone(p, x, y, z, radius, height, c, hanging=False):
    """a spike: hanging = stalactite (from the ceiling), otherwise stalagmite (from the floor)"""
    from ursina.models.procedural.cone import Cone
    e = Entity(parent=p, model=Cone(6, radius=radius, height=height), position=(x, y, z), color=c)
    if hanging:
        e.rotation_x = 180
    return e


def build_cave(sg, d):
    L = sg.L
    HALF = W / 2 + 3.2            # how far the cave walls are from the centre (bigger = wider cave)
    CEIL = 9.5                    # how high the ceiling is
    torch_z = list(range(3, int(L) - 3, 9))
    rock_cols = [(0.30, 0.25, 0.22), (0.25, 0.21, 0.19), (0.36, 0.30, 0.26), (0.21, 0.18, 0.17)]

    # ---- 1. the big mass of rock around the tunnel + grass hill on top ----
    dark = (0.17, 0.14, 0.13)
    for side in (-1, 1):
        box(d, side * (HALF + 16), 8, L / 2 - 6, 32, 24, L + 14, C(dark))
    box(d, 0, CEIL + 8, L / 2 - 6, 130, 12, L + 14, C((0.2, 0.36, 0.17)))
    box(d, 0, CEIL + 1, L / 2 - 6, 2 * HALF + 4, 2, L + 14, C(dark))
    box(d, 0, 5, -11, 2 * HALF + 6, 14, 1.5, C(dark))                       # back wall

    # ---- 2. bumpy walls and ceiling (warmer colour near torches = fake torch light) ----
    z = -10.0
    while z < L + 1:
        warm = min(abs(z - tz) for tz in torch_z) < 3
        for side in (-1, 1):
            for _ in range(3):
                s = random.uniform(1.8, 3.8)
                c = (0.42, 0.3, 0.2) if warm and random.random() < 0.6 else random.choice(rock_cols)
                ball(d, side * (HALF + random.uniform(-0.3, 1.0)), random.uniform(0.3, CEIL - 1), z + random.uniform(-1, 1),
                     s, s * random.uniform(1.0, 1.6), s, C(c, 0.03)).rotation_y = random.uniform(0, 360)
        for _ in range(3):
            s = random.uniform(2, 4)
            ball(d, random.uniform(-HALF, HALF), CEIL - random.uniform(0, 1.2), z + random.uniform(-1, 1),
                 s, s * 0.7, s, C(random.choice(rock_cols), 0.03))
        z += 2.2

    # ---- 3. stalactites (ceiling) and stalagmites (floor) ----
    for _ in range(55):
        h = random.uniform(1.2, 4.0)
        cone(d, random.uniform(-HALF + 1, HALF - 1), CEIL - 0.6, random.uniform(-8, L),
             random.uniform(0.25, 0.6), h, C((0.34, 0.29, 0.26), 0.03), hanging=True).y = CEIL - 0.6 + h * 0 + 0
    for _ in range(26):
        side = random.choice((-1, 1))
        cone(d, side * random.uniform(W / 2 + 0.8, HALF - 0.6), 0, random.uniform(-8, L - 3),
             random.uniform(0.3, 0.7), random.uniform(0.8, 2.4), C((0.3, 0.26, 0.23), 0.03))

    # ---- 4. old wooden mine supports across the tunnel ----
    wood = (0.33, 0.22, 0.13)
    for z in range(8, int(L) - 4, 14):
        for side in (-1, 1):
            box(d, side * (W / 2 + 0.7), 3.6, z, 0.5, 7.2, 0.5, C(wood, 0.03))
        box(d, 0, 7.0, z, W + 2.4, 0.55, 0.6, C(wood, 0.03))
        box(d, -W / 4, 6.2, z, 0.35, 1.6, 0.35, C(wood, 0.03)).rotation_z = 40
        box(d, W / 4, 6.2, z, 0.35, 1.6, 0.35, C(wood, 0.03)).rotation_z = -40

    # ---- 5. loose rocks on the floor along the path edges ----
    for _ in range(40):
        side = random.choice((-1, 1))
        s = random.uniform(0.3, 0.9)
        rock(d, side * random.uniform(W / 2 - 0.2, W / 2 + 1.8), random.uniform(-8, L), s)

    # ---- 6. exit frame: mossy rocks around the opening ----
    for side in (-1, 1):
        for y in (1.5, 4.5, 7.5):
            ball(d, side * (W / 2 + 1.6), y, L + 0.5, 3.4, 3.4, 3.4, C(random.choice(ROCK), 0.04))
    ball(d, 0, CEIL - 0.5, L + 0.5, W + 4, 2.6, 3.2, C(ROCK[1]))
    ball(d, 0, CEIL - 0.5, L + 0.5, W + 2, 0.8, 3.4, C((0.22, 0.42, 0.18)))

    # ---- not combined (they glow / flicker) ----
    sg.flames = []
    for z in torch_z:                                         # torches
        for side in (-1, 1):
            x = side * (W / 2 - 0.2)
            Entity(parent=sg.root, model='cube', color=C(wood), scale=(0.16, 1.1, 0.16), position=(x, 2.0, z))
            f = Entity(parent=sg.root, model='icosphere', color=color.rgb(1.0, 0.55, 0.1),
                       shader=unlit_with_fog_shader, scale=0.5, position=(x, 2.8, z))
            sg.flames.append(f)
            Entity(parent=sg.root, model='icosphere', color=color.rgba(1.0, 0.6, 0.2, 0.10),
                   shader=unlit_shader, scale=1.5, position=(x, 2.8, z))
    cols = [(0.2, 0.9, 1.0), (0.7, 0.3, 1.0), (0.3, 1.0, 0.6)]
    for _ in range(18):                                       # glowing crystals
        side = random.choice((-1, 1))
        c = random.choice(cols)
        x, y, z = side * (HALF - 0.4), random.uniform(0.6, 5.5), random.uniform(-6, L - 6)
        for _ in range(3):
            e = Entity(parent=sg.root, model='diamond', color=color.rgb(*c), shader=unlit_shader,
                       scale=(random.uniform(0.3, 0.5), random.uniform(0.8, 1.6), random.uniform(0.3, 0.5)),
                       position=(x + random.uniform(-0.3, 0.3), y + random.uniform(0, 0.4), z + random.uniform(-0.4, 0.4)))
            e.rotation = (random.uniform(-25, 25), random.uniform(0, 360), random.uniform(-25, 25))
    for _ in range(7):                                        # puddles
        box(sg.root, random.uniform(-W / 2 + 1, W / 2 - 1), 0.03, random.uniform(5, L - 6),
            random.uniform(0.9, 1.8), 0.04, random.uniform(1.5, 3), color.rgb(0.1, 0.2, 0.28), shader=unlit_with_fog_shader)
    # bright daylight at the end of the tunnel
    Entity(parent=sg.root, model='quad', color=color.rgba(1.0, 0.97, 0.75, 0.3), shader=unlit_shader,
           scale=(2 * HALF - 2, CEIL - 1), position=(0, (CEIL - 1) / 2, L + 0.2))


# =====================================================================
#  5. THE CHARACTERS
# =====================================================================
class Human(Entity):
    """a person built from joints: hips, torso, head, 2 arms (shoulder + elbow), 2 legs (hip + knee).
    The 'look' dictionary (see RUNNER_LOOKS) decides colors, hair and extras."""

    def __init__(self, look=None):
        super().__init__()
        look = look or RUNNER_LOOKS[0]
        ex = look['extras']
        skin, shirt, pants = C(look['skin']), C(look['shirt']), C(look['pants'])
        shoe, hair, acc = C(look['shoe']), C(look['hair']), C(look['accent'])
        silver = C((0.8, 0.82, 0.88))
        self.sway = []                                              # things that flap while running (scarf, cape...)
        self.hips = Entity(parent=self, y=0.95)
        box(self.hips, 0, 0.02, 0, 0.38, 0.2, 0.22, pants)
        self.torso = Entity(parent=self.hips, y=0.1)
        box(self.torso, 0, 0.27, 0, 0.44, 0.56, 0.25, shirt)
        if look['pack']:
            box(self.torso, 0, 0.3, -0.2, 0.34, 0.42, 0.16, C(look['pack']))
        self.head = Entity(parent=self.torso, y=0.72)
        h = self.head
        ball(h, 0, 0, 0, 0.27, 0.31, 0.28, skin, model='sphere')
        for sx in (-0.07, 0.07):                                    # eyes (white + colored)
            ball(h, sx, 0.02, 0.122, 0.06, 0.07, 0.04, C((0.97, 0.97, 0.97)), model='sphere')
            ball(h, sx, 0.02, 0.145, 0.04, 0.05, 0.03, C(look['eye']), model='sphere')
        # ---- hair ----
        hs = look['hair_style']
        ball(h, 0, 0.05, -0.04, 0.29, 0.26, 0.29, hair, model='sphere')
        if hs == 'spiky':
            for x, y, z, rx, rz in ((0, 0.2, 0, 0, 0), (0.09, 0.17, 0.03, 0, -28), (-0.09, 0.17, 0.03, 0, 28),
                                    (0, 0.15, -0.11, -45, 0), (0.13, 0.1, -0.06, 0, -62), (-0.13, 0.1, -0.06, 0, 62),
                                    (0.05, 0.15, 0.1, 35, -10), (-0.05, 0.15, 0.1, 35, 10)):
                sp = ball(h, x, y, z, 0.1, 0.3, 0.1, hair, model='diamond')
                sp.rotation_x, sp.rotation_z = rx, rz
        elif hs == 'long':
            box(h, 0, -0.22, -0.11, 0.3, 0.6, 0.08, hair)
            for sx in (-1, 1):
                box(h, sx * 0.14, -0.08, 0.0, 0.05, 0.34, 0.14, hair)
        elif hs == 'twintail':
            for sx in (-1, 1):
                t = box(h, sx * 0.2, -0.22, -0.06, 0.1, 0.52, 0.1, hair)
                self.sway.append((t, sx * 8, 'z'))
                ball(h, sx * 0.2, -0.5, -0.06, 0.13, 0.13, 0.13, hair, model='sphere')
                for k in (-1, 1):                                   # bow
                    b = ball(h, sx * 0.19, 0.1, -0.02, 0.09, 0.14, 0.05, C((1.0, 0.95, 0.5)), model='diamond')
                    b.rotation_z = k * 60
        if look['hat']:
            hat = C(look['hat'])
            box(h, 0, 0.15, 0, 0.52, 0.04, 0.52, hat)
            box(h, 0, 0.21, 0, 0.3, 0.14, 0.3, hat)
        if 'headband' in ex:
            box(h, 0, 0.1, 0, 0.3, 0.05, 0.3, acc)
            box(h, 0, 0.1, 0.152, 0.1, 0.06, 0.02, silver)
            tail = box(h, 0, 0.08, -0.25, 0.06, 0.04, 0.3, acc)
            self.sway.append((tail, 0, 'x'))
        if 'mask' in ex:
            box(h, 0, -0.07, 0.085, 0.22, 0.1, 0.1, C((0.08, 0.08, 0.12)))
        if 'visor' in ex:
            box(h, 0, 0.03, 0.125, 0.27, 0.07, 0.05, acc, shader=unlit_shader)
        # ---- body extras ----
        if 'scarf' in ex:
            box(self.torso, 0, 0.58, 0, 0.5, 0.1, 0.3, acc)
            pv = Entity(parent=self.torso, y=0.58, z=-0.15)
            box(pv, 0, 0, -0.35, 0.12, 0.06, 0.7, acc)
            self.sway.append((pv, 0, 'x'))
        if 'cape' in ex:
            pv = Entity(parent=self.torso, y=0.56, z=-0.15)
            box(pv, 0, -0.45, -0.04, 0.5, 0.9, 0.05, acc)
            box(pv, 0, -0.45, -0.07, 0.46, 0.86, 0.03, C((0.08, 0.1, 0.25)))
            self.sway.append((pv, 6, 'x'))
        if 'katana' in ex:
            kt = box(self.torso, 0.03, 0.3, -0.2, 0.05, 1.0, 0.04, silver)
            kt.rotation_z = 28
            box(self.torso, -0.17, 0.78, -0.2, 0.07, 0.16, 0.06, C((0.15, 0.1, 0.1))).rotation_z = 28
        if 'katana_hip' in ex:
            box(self.hips, -0.27, 0.02, -0.15, 0.05, 0.05, 0.9, silver)
            box(self.hips, -0.27, 0.02, 0.28, 0.07, 0.07, 0.2, C((0.15, 0.1, 0.1)))
        if 'skirt' in ex:
            box(self.hips, 0, -0.1, 0, 0.52, 0.16, 0.36, shirt)
            box(self.hips, 0, -0.19, 0, 0.55, 0.04, 0.39, acc)
        if 'shoulders' in ex:
            for sx in (-1, 1):
                ball(self.torso, sx * 0.3, 0.55, 0, 0.2, 0.12, 0.2, acc, shader=unlit_shader)
        if 'glow' in ex:
            box(self.torso, 0, 0.27, 0.13, 0.03, 0.42, 0.01, acc, shader=unlit_shader)
            box(self.torso, 0, 0.1, 0.13, 0.3, 0.03, 0.01, acc, shader=unlit_shader)
        self.arms, self.legs = [], []
        for sx in (-1, 1):
            sh = Entity(parent=self.torso, position=(sx * 0.29, 0.5, 0))
            box(sh, 0, -0.15, 0, 0.11, 0.3, 0.11, shirt)
            el = Entity(parent=sh, y=-0.3)
            box(el, 0, -0.14, 0, 0.1, 0.28, 0.1, skin)
            ball(el, 0, -0.3, 0, 0.11, 0.11, 0.11, skin, model='sphere')
            if 'wristbands' in ex:
                box(el, 0, -0.04, 0, 0.13, 0.08, 0.13, acc)
            self.arms.append((sh, el))
        for sx in (-1, 1):
            hp = Entity(parent=self.hips, position=(sx * 0.12, -0.02, 0))
            box(hp, 0, -0.23, 0, 0.18, 0.46, 0.19, pants)
            kn = Entity(parent=hp, y=-0.46)
            box(kn, 0, -0.22, 0, 0.15, 0.44, 0.16, pants)
            box(kn, 0, -0.425, 0.07, 0.15, 0.09, 0.3, shoe)
            self.legs.append((hp, kn))

    def pose(self, ph, inten, air, slide, stumble):
        t, h = self.torso, self.hips
        for e, base, axis in self.sway:                           # flapping scarf / cape / pigtails
            if axis == 'x':
                e.rotation_x = -(8 + base) - 22 * inten + 8 * sin(ph * 2)
            else:
                e.rotation_z = base + 6 * sin(ph * 2) * (0.3 + inten)
        if stumble > 0:
            t.rotation_x = 38
            h.y = 0.9
            for i, (hp, kn) in enumerate(self.legs):
                hp.rotation_x = -30 if i else 10
                kn.rotation_x = 30
            for sh, el in self.arms:
                sh.rotation_x = -85
                el.rotation_x = -10
            return
        if slide:
            h.y = 0.42
            t.rotation_x = -50
            for hp, kn in self.legs:
                hp.rotation_x = -80
                kn.rotation_x = 12
            for sh, el in self.arms:
                sh.rotation_x = 35
                el.rotation_x = -10
            return
        h.y = 0.95
        if air:
            t.rotation_x = 14
            for i, (hp, kn) in enumerate(self.legs):
                hp.rotation_x = -60 if i else 25
                kn.rotation_x = 85 if i else 45
            for i, (sh, el) in enumerate(self.arms):
                sh.rotation_x = -80 if i else -30
                el.rotation_x = -40
            return
        A = 18 + 34 * inten
        K = 20 + 75 * inten
        t.rotation_x = 4 + 14 * inten
        t.rotation_y = 6 * sin(ph) * inten
        h.y = 0.95 - 0.05 * abs(sin(ph)) * inten
        for i, (hp, kn) in enumerate(self.legs):
            p = ph + (pi if i else 0)
            hp.rotation_x = -A * sin(p)                      # negative = leg swings forward
            kn.rotation_x = 6 + K * max(0, cos(p))           # knee bends while the leg swings forward
        for i, (sh, el) in enumerate(self.arms):
            p = ph + (0 if i else pi)                        # arms swing opposite to the legs
            sh.rotation_x = -A * 1.05 * sin(p)
            el.rotation_x = -(30 + 50 * inten)


class Bear(Entity):
    """the chaser. The 'look' dictionary (see CHASER_LOOKS) decides colors and extras."""

    def __init__(self, look=None):
        super().__init__()
        look = look or CHASER_LOOKS[0]
        ex = look['extras']
        fur, paw, light, acc = C(look['fur']), C(look['paw']), C(look['light']), C(look['accent'])
        leg_col = paw if 'panda' in ex else fur
        self.sway = []
        self.body = Entity(parent=self, y=1.45)
        b = self.body
        ball(b, 0, 0, 0, 1.5, 1.35, 2.5, fur, model='sphere')
        ball(b, 0, 0.35, 0.9, 1.5, 1.3, 1.4, fur, model='sphere')
        self.head = Entity(parent=b, position=(0, 0.3, 1.75))
        h = self.head
        ball(h, 0, 0, 0, 0.95, 0.85, 0.95, fur, model='sphere')
        ball(h, 0, -0.2, 0.5, 0.5, 0.4, 0.55, light, model='sphere')
        ball(h, 0, -0.08, 0.78, 0.2, 0.15, 0.15, C((0.05, 0.05, 0.05)), model='sphere')
        ear_col = paw if 'panda' in ex else fur
        if 'fox_ears' not in ex:
            for sx in (-1, 1):
                ball(h, sx * 0.35, 0.45, -0.05, 0.3, 0.3, 0.2, ear_col, model='sphere')
        for sx in (-1, 1):
            ball(h, sx * 0.25, 0.12, 0.42, 0.11, 0.11, 0.11, C(look['eye']), model='sphere', shader=unlit_shader)
        if 'panda' in ex:
            for sx in (-1, 1):
                ball(h, sx * 0.27, 0.12, 0.38, 0.24, 0.3, 0.12, C((0.05, 0.05, 0.05)), model='sphere')
                ball(h, sx * 0.25, 0.12, 0.45, 0.11, 0.11, 0.11, C(look['eye']), model='sphere', shader=unlit_shader)
            ball(b, 0, 0.3, 0.9, 1.56, 0.9, 0.55, paw, model='sphere')
        if 'horns' in ex:
            for sx in (-1, 1):
                hn = ball(h, sx * 0.28, 0.55, 0.05, 0.16, 0.55, 0.16, acc, model='diamond')
                hn.rotation_z = -sx * 22
        if 'fox_ears' in ex:
            for sx in (-1, 1):
                e = ball(h, sx * 0.3, 0.6, -0.05, 0.3, 0.7, 0.12, fur, model='diamond')
                e.rotation_z = -sx * 15
                ball(h, sx * 0.3, 0.58, 0.0, 0.16, 0.4, 0.06, acc, model='diamond').rotation_z = -sx * 15
        if 'spikes' in ex or 'ice' in ex or 'wisps' in ex:
            glow = 'ice' in ex or 'wisps' in ex
            for i in range(5):
                sp = ball(b, 0, 0.85 + (0.12 if i in (1, 2, 3) else 0), -0.9 + i * 0.5, 0.2, 0.55 if i in (1, 2, 3) else 0.4, 0.2,
                          acc, model='diamond', **({'shader': unlit_shader} if glow else {}))
        if 'tails' in ex:
            for k, ang in enumerate((-28, 0, 28)):
                pv = Entity(parent=b, position=(0, 0.2, -1.1))
                pv.rotation_y = ang
                ball(pv, 0, 0.2, -0.8, 0.5, 0.5, 1.4, fur, model='sphere')
                ball(pv, 0, 0.2, -1.4, 0.4, 0.4, 0.6, acc, model='sphere')
                self.sway.append(pv)
        self.legs = []
        for sz in (0.85, -0.85):
            for sx in (-0.55, 0.55):
                hp = Entity(parent=b, position=(sx, -0.3, sz))
                box(hp, 0, -0.55, 0, 0.45, 1.0, 0.5, leg_col)
                box(hp, 0, -1.05, 0.1, 0.5, 0.15, 0.6, paw)
                self.legs.append(hp)
        self.scale = 1.25

    def gallop(self, g):
        self.body.y = 1.45 + 0.2 * abs(sin(g))
        self.body.rotation_x = 5 * sin(g + 0.6)
        self.head.rotation_x = -6 * sin(g)
        for i, hp in enumerate(self.legs):
            front = i < 2
            hp.rotation_x = -42 * sin(g + (0 if front else pi * 0.75))
        for i, pv in enumerate(self.sway):
            pv.rotation_x = -12 + 10 * sin(g * 2 + i)


# =====================================================================
#  6. OBSTACLES AND COINS
# =====================================================================
class Ob:
    def __init__(self, kind, s, lat, hw, hd, ymax=99, slide_ok=False, e=None, active=True):
        self.kind, self.s, self.lat, self.hw, self.hd = kind, s, lat, hw, hd
        self.ymax, self.slide_ok, self.e, self.active = ymax, slide_ok, e, active
        self.hit = False


def add_log(sg, lat, s, w, biome):
    g = Entity(parent=sg.root, position=(lat, 0, s))
    c = (0.38, 0.25, 0.14) if biome != 'ruins' else (0.55, 0.54, 0.48)
    box(g, 0, 0.38, 0, w, 0.76, 0.85, C(c, 0.03))
    box(g, 0, 0.78, 0, w * 0.9, 0.07, 0.6, C((0.2, 0.42, 0.16)))
    sg.obs.append(Ob('log', s, lat, w / 2 + 0.2, 0.65, ymax=0.78, e=g))


def add_boulder(sg, lat, s):
    g = Entity(parent=sg.root, position=(lat, 0, s))
    b = ball(g, 0, 1.0, 0, 2.3, 2.1, 2.3, C(random.choice(ROCK), 0.03))
    b.rotation_y = random.uniform(0, 360)
    ball(g, 0.9, 0.35, 0.5, 1.0, 0.7, 1.0, C(ROCK[2]))
    sg.obs.append(Ob('boulder', s, lat, 1.15, 1.05, ymax=1.9, e=g))


def add_branch(sg, s, biome):
    g = Entity(parent=sg.root, position=(0, 0, s))
    wood = C(BROWN, 0.03) if biome != 'ruins' else C((0.55, 0.54, 0.48))
    for side in (-1, 1):
        box(g, side * (W / 2 + 0.5), 1.8, 0, 0.55, 3.6, 0.55, wood)
        ball(g, side * (W / 2 + 0.3), 3.4, 0, 1.8, 1.2, 1.8, C(random.choice(GREENS), 0.03))
    box(g, 0, 1.6, 0, W + 1.4, 0.5, 0.55, wood)
    for x in (-2.5, 0.5, 2.8):
        ball(g, x, 1.95, 0, 1.6, 0.8, 1.2, C(random.choice(GREENS), 0.03))
    sg.obs.append(Ob('branch', s, 0, W, 0.5, slide_ok=True, e=g))


def add_pit(sg, lats, s, biome):
    lo, hi = min(lats), max(lats)
    w = (hi - lo) + 2.4
    cx = (lo + hi) / 2
    g = Entity(parent=sg.root, position=(cx, 0, s))
    dark = (0.04, 0.03, 0.03) if biome != 'river' else (0.08, 0.3, 0.42)
    box(g, 0, 0.03, 0, w, 0.06, 2.8, C(dark), shader=unlit_with_fog_shader)
    for z in (-1.45, 1.45):
        box(g, 0, 0.1, z, w + 0.4, 0.2, 0.35, C((0.36, 0.25, 0.15), 0.03))
    sg.obs.append(Ob('pit', s, cx, w / 2, 1.4, ymax=0.3, e=g))


def add_vine(sg, s):
    g = Entity(parent=sg.root, position=(0, 0, s))
    pivot = Entity(parent=g, y=7.6)
    box(pivot, 0, -3.1, 0, 0.1, 6.2, 0.1, C((0.2, 0.45, 0.18)))
    ball(pivot, 0, -6.2, 0, 1.1, 1.1, 1.1, C((0.2, 0.5, 0.18)))
    o = Ob('vine', s, 0, 0.85, 0.7, ymax=1.6, slide_ok=True, e=g)
    o.pivot, o.phase, o.speed = pivot, random.uniform(0, 6.28), random.uniform(1.5, 2.1)
    sg.obs.append(o)


def add_roller(sg, s):
    g = Entity(parent=sg.root, position=(0, 0, s))
    r = ball(g, 0, 0.6, 0, 1.3, 1.3, 1.3, C((0.5, 0.45, 0.4)))
    o = Ob('roller', s, 0, 0.8, 0.85, ymax=1.0, e=g)
    o.ball, o.phase, o.speed = r, random.uniform(0, 6.28), random.uniform(1.2, 1.7)
    sg.obs.append(o)


def add_faller(sg, s, biome):
    """a tree (or pillar) that collapses across the path when you get close"""
    side = random.choice((-1, 1))
    pivot = Entity(parent=sg.root, position=(side * (W / 2 + 1.7), 0.5, s))
    if biome in ('ruins', 'rocks'):
        box(pivot, 0, 5, 0, 1.2, 10, 1.2, C((0.55, 0.54, 0.48), 0.03))
        box(pivot, 0, 10.2, 0, 1.7, 0.5, 1.7, C((0.5, 0.49, 0.44)))
    else:
        box(pivot, 0, 5, 0, 0.9, 10, 0.9, C(BROWN, 0.03))
        ball(pivot, 0, 10.5, 0, 5, 4, 5, C(random.choice(GREENS), 0.03))
    o = Ob('faller', s, 0, W / 2 + 0.6, 0.8, ymax=1.0, e=pivot, active=False)
    o.side, o.fell = side, False
    sg.obs.append(o)


def add_coin(sg, lat, s, y=1.0):
    c = Entity(parent=sg.root, model='icosphere', color=color.gold, shader=unlit_with_fog_shader,
               scale=(0.6, 0.6, 0.14), position=(lat, y, s))
    c.s, c.lat, c.y0 = s, lat, y
    sg.coins.append(c)


def coin_line(sg, lane, s, n=5):
    for i in range(n):
        add_coin(sg, LANES[lane], s + i * 2)


def coin_arc(sg, lane, s, n=7):
    for i in range(n):
        add_coin(sg, LANES[lane], s - 6 + i * 2, 1.0 + 1.4 * sin(pi * i / (n - 1)))


KINDS = {
    'jungle': ['log', 'boulder', 'branch', 'pit', 'vine', 'roller'],
    'river': ['log', 'pit', 'pit', 'branch', 'vine', 'roller'],
    'rocks': ['boulder', 'boulder', 'roller', 'pit', 'log', 'branch'],
    'ruins': ['log', 'boulder', 'branch', 'pit', 'vine', 'roller'],
}


def place_obstacles(sg):
    if sg.biome == 'cave':
        return
    s = max(8, MIN_OBSTACLE_DIST - sg.start)
    last = None
    while s < sg.L - 28:
        kind = random.choice(KINDS[sg.biome])
        if kind == last:
            kind = random.choice(KINDS[sg.biome])
        last = kind
        lanes = [0, 1, 2]
        if kind == 'log':
            ls = random.sample(lanes, random.choice([1, 2, 3]))
            if len(ls) == 3:
                add_log(sg, 0, s, W + 0.6, sg.biome)
            else:
                for l in ls:
                    add_log(sg, LANES[l], s, 2.1, sg.biome)
            coin_arc(sg, ls[0], s)
        elif kind == 'boulder':
            ls = random.sample(lanes, random.choice([1, 2]))
            for l in ls:
                add_boulder(sg, LANES[l], s)
            free = [l for l in lanes if l not in ls]
            coin_line(sg, random.choice(free), s - 4)
        elif kind == 'branch':
            add_branch(sg, s, sg.biome)
            coin_line(sg, random.choice(lanes), s + 4, 4)
        elif kind == 'pit':
            ls = random.sample(lanes, random.choice([1, 2, 3]))
            add_pit(sg, [LANES[l] for l in ls], s, sg.biome)
            coin_arc(sg, ls[0], s)
        elif kind == 'vine':
            add_vine(sg, s)
            coin_line(sg, random.choice(lanes), s + 5, 4)
        elif kind == 'roller':
            add_roller(sg, s)
            coin_line(sg, random.choice(lanes), s - 5, 4)
        elif kind == 'faller':
            add_faller(sg, s, sg.biome)
            coin_line(sg, random.choice(lanes), s - 8, 4)
        s += random.uniform(18, 26) if sg.start < 300 else random.uniform(15, 22)


# =====================================================================
#  7. BUILDING THE WORLD (path pieces with corners)
# =====================================================================
class Seg:
    pass


def rect_of(origin, h, total, hw):
    d, r = fwd(h), rgt(h)
    pts = [origin + r * hw, origin - r * hw, origin + d * total + r * hw, origin + d * total - r * hw]
    xs, zs = [p.x for p in pts], [p.z for p in pts]
    return (min(xs), max(xs), min(zs), max(zs))


def overlap(a, b):
    return not (a[1] < b[0] or b[1] < a[0] or a[3] < b[2] or b[3] < a[2])


def after(origin, h, L, turn):
    """where the NEXT piece of path starts"""
    if turn == 0:
        return origin + fwd(h) * L, h
    nh = (h + turn) % 4
    center = origin + fwd(h) * (L + W / 2)
    return center + fwd(nh) * (W / 2), nh


def choose_turn(origin, h, L):
    opts = [1, -1]
    random.shuffle(opts)
    if len(st.turns) >= 2 and st.turns[-1] == st.turns[-2] != 0:
        opts.sort(key=lambda t: t == st.turns[-1])            # avoid a 3rd turn the same way
    for t in opts:
        no, nh = after(origin, h, L, t)
        rc = rect_of(no, nh, 110 + W, 30)
        if all(not overlap(rc, g.rect) for g in st.segs):
            return t
    return 0


def build_ground(sg):
    r, b, T = sg.root, sg.biome, sg.total
    s0 = -10 if sg.idx == 0 else 0
    Ls = T - s0
    cz = s0 + Ls / 2
    off = (sg.idx % 6) * 0.03
    if b == 'river':
        sg.water = box(r, 0, -1.9, cz, 130, 0.2, Ls, C((0.1, 0.45, 0.56)), texture='perlin_noise',
                       texture_scale=(30, Ls / 6), shader=unlit_with_fog_shader)
        for side in (-1, 1):
            box(r, side * (16 + 30), -0.9 - off, cz, 60, 1, Ls, C((0.5, 0.78, 0.4)), texture='grass',
                texture_scale=(15, Ls / 4))
        p = Entity(parent=r)
        for i in range(int(Ls / 0.75)):
            box(p, 0, -0.1, s0 + i * 0.75 + 0.37, W, 0.2, 0.66, C((0.5, 0.35, 0.2), 0.05))
        for side in (-1, 1):
            box(p, side * (W / 2 - 0.4), -0.5, cz, 0.4, 0.5, Ls, C((0.3, 0.2, 0.12)))
        p.combine(include_normals=True)
        return
    tex, tcol = {'jungle': ('grass', (0.55, 0.8, 0.45)), 'rocks': ('perlin_noise', (0.55, 0.45, 0.35)),
                 'ruins': ('grass', (0.5, 0.75, 0.42)), 'cave': ('perlin_noise', (0.3, 0.25, 0.22))}[b]
    box(r, 0, -0.9 - off, cz, 130, 1, Ls, C(tcol), texture=tex, texture_scale=(32, Ls / 4))
    pc = {'jungle': (0.55, 0.4, 0.25), 'rocks': (0.62, 0.55, 0.45), 'ruins': (0.6, 0.58, 0.52),
          'cave': (0.35, 0.3, 0.26)}[b]
    box(r, 0, -0.5, cz, W, 1, Ls, C(pc), texture='brick' if b == 'ruins' else 'perlin_noise', texture_scale=(W, Ls / 2))


def build_seg(origin, h, L, biome, turn, start, idx):
    sg = Seg()
    sg.origin, sg.h, sg.L, sg.biome, sg.turn, sg.start, sg.idx = origin, h, L, biome, turn, start, idx
    sg.cw = W if turn else 0
    sg.total = L + sg.cw
    sg.root = Entity(position=origin, rotation_y=h * 90)
    sg.obs, sg.coins, sg.flames, sg.water, sg.next = [], [], [], None, None
    sg.rect = rect_of(origin, h, sg.total, 30)
    build_ground(sg)
    decorate(sg)
    if turn:                                                    # arrow on the corner tile
        cz = L + W / 2
        sgn = turn
        yel = C((1.0, 0.85, 0.1))
        box(sg.root, 0, 0.03, cz, 2.4, 0.05, 0.45, yel, shader=unlit_shader).x = 0
        for k in (-1, 1):
            a = box(sg.root, sgn * 0.9, 0.03, cz + k * 0.45, 1.5, 0.05, 0.4, yel, shader=unlit_shader)
            a.rotation_y = -sgn * k * 40
            a.x = sgn * 0.85
    place_obstacles(sg)
    return sg


def add_seg():
    prev = st.segs[-1]
    origin, h = after(prev.origin, prev.h, prev.L, prev.turn)
    start = prev.start + prev.L + prev.cw
    idx = prev.idx + 1
    opts = [b for b in ['jungle', 'jungle', 'river', 'rocks', 'ruins'] if b != prev.biome]
    biome = 'jungle' if idx == 1 else random.choice(opts)
    L = random.randint(80, 110)
    turn = choose_turn(origin, h, L)
    st.turns.append(turn)
    sg = build_seg(origin, h, L, biome, turn, start, idx)
    prev.next = sg
    st.segs.append(sg)


# =====================================================================
#  8. EFFECTS
# =====================================================================
def burst(pos, col, n=10):
    for _ in range(n):
        p = Entity(model='cube', color=col, scale=0.18, position=pos, shader=unlit_with_fog_shader)
        p.animate_position(pos + Vec3(random.uniform(-1.5, 1.5), random.uniform(0.5, 2), random.uniform(-1.5, 1.5)),
                           duration=0.5, curve=curve.out_expo)
        p.animate_scale(0, duration=0.5)
        destroy(p, delay=0.55)


def red_flash():
    flash.color = color.rgba(1, 0, 0, 0.35)
    flash.animate_color(color.rgba(1, 0, 0, 0), duration=0.35)


# =====================================================================
#  9. GAME FLOW
# =====================================================================
player = Human()
bear = Bear()
load_step(0.72, 'Creating characters')


def new_run(menu=False):
    for sg in getattr(st, 'segs', []):
        kill(sg.root)
    st.segs, st.turns = [], []
    # the cave is the first piece of path
    cave = build_seg(Vec3(0, 0, 0), 0, CAVE_LEN, 'cave', 0, 0, 0)
    st.segs.append(cave)
    while len(st.segs) < 3:
        add_seg()
    st.seg = cave
    st.s, st.lat, st.lane = 6.0, 0.0, 1
    st.speed, st.vy, st.y, st.grounded = 2.5, 0.0, 0.0, True
    st.slide_t, st.stumble, st.pending = 0.0, 0.0, 0
    st.gap, st.coins, st.shake, st.clock = START_GAP, 0, 0.0, 0.0
    st.cum, st.ph, st.bph = START_CUM, 0.0, 0.0
    st.last_strike, st.last_bear_strike, st.roar_t = 0, 0, 3.0
    st.over, st.cam_yaw, st.yaw = False, 0.0, 0.0
    st.trail = [(float(i), 0.0, -25.0 + i, 0.0) for i in range(32)]
    st.best = getattr(st, 'best', 0)
    st.reason = ''
    bear.position = Vec3(0, 0, -START_GAP)
    overlay.enabled = False
    turn_text.text = ''
    player.position = Vec3(0, 0, st.s)
    player.rotation_y = 0
    st.menu_ready = menu
    if menu:                                  # just show the cave behind the menu
        center_text.text = ''
        player.pose(0, 0, False, False, 0)
        bear.gallop(0)
    else:
        begin_run()


def begin_run():
    st.menu_ready = False
    center_text.text = 'A / D = lane & turn     SPACE = jump     S = slide'
    invoke(clear_hint, delay=4)
    play(s_roar, 0.6, 0.9)


def clear_hint():
    if not st.over:
        center_text.text = ''


def game_over(reason):
    st.over = True
    score = int(st.cum - START_CUM) + st.coins * 10
    st.best = max(st.best, score)
    play(s_hit, 1.0)
    play(s_roar, 1.0, 0.85)
    st.shake = 1.5
    red_flash()
    overlay.enabled = True
    center_text.text = f'{reason}\n\nScore: {score}    Best: {st.best}\n\nPress R to restart     M = menu'


def hit_obstacle(o):
    o.hit = True
    st.stumble = 0.55
    st.speed = max(7.0, st.speed * 0.72)
    st.gap -= 2.8
    st.shake = 1.0
    play(s_hit, 0.9)
    if random.random() < 0.7:
        play(s_roar, 0.8, random.uniform(0.9, 1.05))
    burst(player.position + Vec3(0, 1, 0), color.rgb(0.9, 0.5, 0.3), 14)
    red_flash()
    if st.gap <= CAUGHT_GAP:
        game_over('THE BEAR CAUGHT YOU!')


def do_turn():
    sg = st.seg
    P = sg.origin + fwd(sg.h) * st.s + rgt(sg.h) * st.lat
    nx = sg.next
    rel = P - nx.origin
    st.s = dot(rel, fwd(nx.h))
    st.lat = dot(rel, rgt(nx.h))
    st.seg = nx
    st.pending = 0
    st.lane = 1
    st.shake = 0.15
    # clean up old pieces (keep the one right behind us)
    for g in list(st.segs):
        if g.idx < sg.idx:
            kill(g.root)
            st.segs.remove(g)
    while len(st.segs) < 4:
        add_seg()


def trail_pos(target):
    tr = st.trail
    i = len(tr) - 1
    while i > 0 and tr[i][0] > target:
        i -= 1
    a = tr[i]
    b = tr[min(i + 1, len(tr) - 1)]
    span = b[0] - a[0]
    k = 0 if span <= 0 else max(0, min(1, (target - a[0]) / span))
    return a[1] + (b[1] - a[1]) * k, a[2] + (b[2] - a[2]) * k, a[3]


def input(key):
    if MODE == 'loading':
        return
    if MODE != 'play':
        if MODE == 'menu' and key in ('enter', 'space'):
            start_game()
        elif key == 'escape':
            if MODE == 'skins':
                show_menu(rebuild=False)
            else:
                application.quit()
        return
    if st.over:
        if key == 'r':
            new_run()
        elif key == 'm':
            show_menu()
        elif key == 'escape':
            application.quit()
        return
    sg = st.seg
    in_turn_zone = sg.turn != 0 and st.s >= sg.L - 7
    left = key in ('left arrow', 'a')
    right = key in ('right arrow', 'd')
    if left or right:
        if in_turn_zone:
            if (right and sg.turn == 1) or (left and sg.turn == -1):
                st.pending = sg.turn
        else:
            if left and st.lane > 0:
                st.lane -= 1
            if right and st.lane < 2:
                st.lane += 1
    if key in ('space', 'up arrow', 'w') and st.grounded and st.stumble <= 0:
        st.vy = 9.2
        st.grounded = False
        st.slide_t = 0
        play(s_jump, 0.6, random.uniform(0.95, 1.05))
    if key in ('s', 'down arrow'):
        if st.grounded:
            st.slide_t = 0.75
        else:
            st.vy = -14
            st.slide_t = 0.75
    if key == 'escape':
        application.quit()


def menu_update(dt):
    st.clock += dt
    for sg in st.segs:
        for f in sg.flames:
            f.scale = 0.5 + 0.1 * sin(st.clock * 12 + f.z)
    if MODE == 'skins':                                         # runner and chaser side by side, above the skin cards
        player.position = Vec3(1.8, 0, 6)
        player.rotation_y = 20 * sin(st.clock * 0.8)
        bear.position = Vec3(-2.3, 0, 5)
        bear.rotation_y = -15 * sin(st.clock * 0.8)
        camera.position = Vec3(0, 1.7, 22)
        camera.rotation = Vec3(10, 180, 0)
        camera.fov = lerp(camera.fov, 55, 6 * dt)
    else:                                                       # main menu: the camera slowly swings around them
        player.position = Vec3(0, 0, 6)
        player.rotation_y = 0
        bear.position = Vec3(0, 0, -START_GAP)
        bear.rotation_y = 0
        center = Vec3(0, 1.2, 2.0)
        a = 0.6 * sin(st.clock * 0.35)
        camera.position = center + Vec3(sin(a) * 5.5, 1.4, cos(a) * 10.5)
        d = center + Vec3(2.2, 0, 0) - camera.position          # point the camera at the target (no tilt)
        camera.rotation = Vec3(degrees(atan2(-d.y, sqrt(d.x ** 2 + d.z ** 2))), degrees(atan2(d.x, d.z)), 0)
        camera.fov = lerp(camera.fov, 55, 4 * dt)
    player.torso.rotation_x = 4 + 2 * sin(st.clock * 2)
    bear.head.rotation_y = 12 * sin(st.clock * 1.3)
    if s_amb and not s_amb.playing:
        s_amb.volume = 0.3
        s_amb.play()


def update():
    dt = min(time.dt, 0.05)
    if MODE != 'play':
        if MODE != 'loading':
            menu_update(dt)
        return
    st.clock += dt
    cur = st.seg
    for sg in st.segs:
        if sg.water:
            sg.water.texture_offset = (0, -st.clock * 0.08)
        for f in sg.flames:
            f.scale = 0.5 + 0.1 * sin(st.clock * 12 + f.z)
    if st.over:
        return

    # ---------- speed: slow start, fast later ----------
    if st.speed < 12:
        st.speed += 3.2 * dt
    else:
        st.speed = min(24, st.speed + 0.2 * dt)
    spd = st.speed
    ds = spd * dt
    st.s += ds
    st.cum += ds
    st.stumble = max(0, st.stumble - dt)
    st.slide_t = max(0, st.slide_t - dt)

    # ---------- corners ----------
    sg = st.seg
    if sg.turn == 0:
        if st.s >= sg.L:
            st.s -= sg.L
            st.seg = sg.next
            for g in list(st.segs):
                if g.idx < sg.idx:
                    kill(g.root)
                    st.segs.remove(g)
            while len(st.segs) < 4:
                add_seg()
            sg = st.seg
    else:
        if st.pending and st.s >= sg.L - 0.2:
            do_turn()
            sg = st.seg
        elif st.s > sg.L + W - 0.6:
            game_over('YOU MISSED THE TURN!')
            return

    # ---------- lane, jump, slide ----------
    st.lat += (LANES[st.lane] - st.lat) * min(1, 11 * dt)
    was_air = not st.grounded
    st.vy -= 26 * dt
    st.y += st.vy * dt
    if st.y <= 0:
        st.y = 0
        st.vy = 0
        st.grounded = True
        if was_air:
            play(s_land, 0.7)
            burst(player.position + Vec3(0, 0.1, 0), color.rgb(0.8, 0.65, 0.5), 6)
    sliding = st.slide_t > 0 and st.grounded

    # ---------- place the runner ----------
    pos = sg.origin + fwd(sg.h) * st.s + rgt(sg.h) * st.lat + Vec3(0, st.y, 0)
    player.position = pos
    target_yaw = sg.h * 90
    st.yaw += ((target_yaw - st.yaw + 180) % 360 - 180) * min(1, 12 * dt)
    player.rotation_y = st.yaw
    player.rotation_z = (LANES[st.lane] - st.lat) * 4
    inten = max(0, min(1, (spd - 2) / 12))
    st.ph += (4 + 0.33 * spd) * dt
    player.pose(st.ph, inten, not st.grounded, sliding, st.stumble)
    strike = int((st.ph - pi / 2) // pi)
    if strike != st.last_strike:
        st.last_strike = strike
        if st.grounded and not sliding and st.stumble <= 0:
            play(random.choice(s_steps), 0.3 + 0.5 * inten, random.uniform(0.9, 1.1))

    # ---------- the bear follows your footsteps ----------
    st.trail.append((st.cum, pos.x, pos.z, st.yaw))
    if len(st.trail) > 900:
        st.trail = st.trail[-700:]
    st.gap = min(START_GAP, st.gap + 0.45 * dt)
    bx, bz, byaw = trail_pos(st.cum - st.gap)
    bear.position = Vec3(bx, 0, bz)
    bear.rotation_y = byaw
    st.bph += (3.5 + 0.4 * spd) * dt
    bear.gallop(st.bph)
    bstrike = int(st.bph // pi)
    if bstrike != st.last_bear_strike:
        st.last_bear_strike = bstrike
        play(s_bear, max(0.15, min(1, 1.1 - st.gap / 14)), random.uniform(0.85, 1.0))
    st.roar_t -= dt
    if st.roar_t <= 0:
        st.roar_t = random.uniform(5, 8) if st.gap > 5 else random.uniform(2, 3.5)
        play(s_roar, max(0.35, min(1, 1.2 - st.gap / 12)), random.uniform(0.9, 1.05))
    if st.gap <= CAUGHT_GAP:
        game_over('THE BEAR CAUGHT YOU!')
        return

    # ---------- obstacles ----------
    for g in (sg, sg.next):
        if g is None:
            continue
        for o in g.obs:
            if o.kind == 'vine':
                o.lat = 3.3 * sin(o.speed * st.clock + o.phase)
                o.pivot.rotation_z = -degrees(asin(max(-0.95, min(0.95, o.lat / 6.2))))
            elif o.kind == 'roller':
                o.lat = 3.4 * sin(o.speed * st.clock + o.phase)
                o.e.x = o.lat
                o.ball.rotation_z = -o.lat * 40
            elif o.kind == 'faller' and not o.fell and g is sg and 0 < o.s - st.s < spd * 1.05 + 6:
                o.fell = True
                o.e.animate('rotation_z', -o.side * 90, duration=0.85, curve=curve.in_quad)
                play(s_collapse, 1.0, random.uniform(0.9, 1.05))
                st.shake = max(st.shake, 0.5)
                invoke(setattr, o, 'active', True, delay=0.8)
                invoke(burst, o.e.world_position + Vec3(0, 0.5, 0), color.rgb(0.6, 0.5, 0.4), 12, delay=0.85)
    for o in sg.obs:
        if o.hit or not o.active:
            continue
        if abs(st.s - o.s) < o.hd and abs(st.lat - o.lat) < o.hw and st.y < o.ymax:
            if o.slide_ok and sliding:
                continue
            hit_obstacle(o)
            if st.over:
                return

    # ---------- coins ----------
    for g in (sg, sg.next):
        if g is None:
            continue
        for c in g.coins[:]:
            c.rotation_y += 240 * dt
            if g is sg and abs(c.s - st.s) < 1.0 and abs(c.lat - st.lat) < 1.1 and abs(c.y0 - (st.y + 0.9)) < 1.1:
                burst(c.world_position, color.gold, 7)
                play(s_coin, 0.5, random.uniform(0.95, 1.15))
                destroy(c)
                g.coins.remove(c)
                st.coins += 1

    # ---------- camera ----------
    st.cam_yaw += ((sg.h * 90 - st.cam_yaw + 180) % 360 - 180) * min(1, 5.5 * dt)
    f = Vec3(sin(radians(st.cam_yaw)), 0, cos(radians(st.cam_yaw)))
    st.shake = max(0, st.shake - 3 * dt)
    camera.position = pos - f * 7.4 + Vec3(random.uniform(-1, 1) * st.shake * 0.25,
                                           4.4 + random.uniform(-1, 1) * st.shake * 0.25, 0)
    camera.rotation_y = st.cam_yaw
    camera.rotation_x = 17
    camera.fov = lerp(camera.fov, 78 + (spd - 6) * 0.9, 3 * dt)
    sun.position = Vec3(pos.x, 0, pos.z) + f * 25

    # ---------- sound of the places ----------
    if s_river:
        s_river.volume = lerp(s_river.volume, 0.9 if sg.biome == 'river' else 0.0, 2 * dt)
        if not s_river.playing:
            s_river.play()
    if s_amb and not s_amb.playing:
        s_amb.play()

    # ---------- UI ----------
    tl = window.top_left
    score_text.position = (tl.x + 0.03, 0.47)
    coin_text.position = (tl.x + 0.03, 0.42)
    score_text.text = f'Score: {int(st.cum - START_CUM) + st.coins * 10}'
    coin_text.text = f'Coins: {st.coins}'
    danger_fill.scale_x = 0.3 * max(0, min(1, (START_GAP - st.gap) / (START_GAP - CAUGHT_GAP)))
    if sg.turn and sg.L - 35 < st.s < sg.L + W:
        turn_text.text = '>>> TURN RIGHT  (D)' if sg.turn == 1 else '<<< TURN LEFT  (A)'
    else:
        turn_text.text = ''


load_step(0.8, 'Building the jungle')
new_run(menu=True)
load_step(1.0, 'Ready!')
invoke(show_menu, False, delay=0.6)

if __name__ == '__main__':
    app.run()