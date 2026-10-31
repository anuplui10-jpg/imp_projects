# sounds.py
# All the game's sounds are made by code, so you do not need any sound files.
#   * engine: 8 looping engine sounds. The game crossfades between them so the
#     pitch rises and falls with the bike's speed.
#   * effects: click, coin, checkpoint, land, crash, stunt, countdown, finish...
#   * music: a short, quiet chiptune loop (press M in the game to mute it all,
#     or set MUSIC = False below to turn the music off for good).

import array
import math
import random

import pygame

MUSIC = True


class Sounds:
    LEVELS = 8                      # number of engine pitch levels

    def __init__(self):
        self.ok = False
        self.muted = False
        self.engine_silent = True
        self.music_level = 0.2
        info = pygame.mixer.get_init()
        if not info:
            try:
                pygame.mixer.init(22050, -16, 1, 512, allowedchanges=0)
            except (pygame.error, TypeError):
                return
            info = pygame.mixer.get_init()
        if not info:
            return
        self.rate, fmt, self.channels = info
        if fmt != -16 or self.channels not in (1, 2):
            return
        try:
            pygame.mixer.set_num_channels(24)
            pygame.mixer.set_reserved(self.LEVELS + 1)
            self.sounds = {}
            self._build_effects()
            self._build_engine()
            self._build_music()
            self.ok = True
        except Exception:                       # never let sound crash the game
            self.ok = False

    # ------------------------------------------------------------------
    # tiny synthesiser
    # ------------------------------------------------------------------
    def _make(self, samples):
        data = array.array("h", (int(max(-1.0, min(1.0, s)) * 30000) for s in samples))
        if self.channels == 2:
            stereo = array.array("h")
            for v in data:
                stereo.append(v)
                stereo.append(v)
            data = stereo
        return pygame.mixer.Sound(buffer=data.tobytes())

    def _tone(self, freq, dur, vol=0.5, decay=5.0, wave="sine", sweep=0.0):
        n = int(self.rate * dur)
        out = []
        phase = 0.0
        two_pi = math.tau
        attack = self.rate * 0.004
        for i in range(n):
            t = i / self.rate
            phase += two_pi * (freq + sweep * t) / self.rate
            if wave == "square":
                s = 0.6 if math.sin(phase) >= 0 else -0.6
            elif wave == "tri":
                s = (2 / math.pi) * math.asin(math.sin(phase))
            else:
                s = math.sin(phase)
            env = math.exp(-decay * i / n) * (1.0 if i > attack else i / attack)
            out.append(s * env * vol)
        return out

    def _noise(self, dur, vol=0.5, decay=6.0, lowpass=0.3, seed=1):
        rnd = random.Random(seed)
        n = int(self.rate * dur)
        out, y = [], 0.0
        for i in range(n):
            y += lowpass * (rnd.uniform(-1, 1) - y)
            out.append(y * math.exp(-decay * i / n) * vol)
        return out

    @staticmethod
    def _mix(a, b):
        if len(a) < len(b):
            a, b = b, a
        out = list(a)
        for i, v in enumerate(b):
            out[i] += v
        return out

    def _seq(self, notes, vol=0.5, wave="sine", decay=5.0):
        out = []
        for freq, dur in notes:
            out += self._tone(freq, dur, vol, decay, wave)
        return out

    # ------------------------------------------------------------------
    # sound effects
    # ------------------------------------------------------------------
    def _build_effects(self):
        s = self.sounds
        mk = self._make
        s["click"] = mk(self._tone(900, 0.07, 0.45, 6, "sine", 1500))
        s["beep"] = mk(self._tone(520, 0.16, 0.5, 2.5, "square"))
        s["go"] = mk(self._tone(880, 0.45, 0.5, 2.5, "square"))
        s["coin"] = mk(self._seq([(1175, 0.07), (1568, 0.2)], 0.45, "sine", 5))
        s["checkpoint"] = mk(self._seq([(659, 0.1), (784, 0.1), (1047, 0.3)], 0.45, "tri", 3))
        s["stunt"] = mk(self._seq([(523, 0.07), (659, 0.07), (784, 0.07), (1047, 0.07), (1319, 0.25)],
                                  0.45, "tri", 3))
        s["land"] = mk(self._mix(self._tone(85, 0.2, 0.9, 6, "sine", -40),
                                 self._noise(0.07, 0.5, 8, 0.4, 3)))
        s["crash"] = mk(self._mix(self._noise(0.7, 0.9, 5, 0.22, 5),
                                  self._tone(75, 0.4, 0.8, 5, "sine", -40)))
        s["finish"] = mk(self._seq([(523, 0.13), (659, 0.13), (784, 0.13), (1047, 0.55)], 0.45, "tri", 2))
        s["star0"] = mk(self._tone(880, 0.35, 0.45, 4, "tri"))
        s["star1"] = mk(self._tone(1047, 0.35, 0.45, 4, "tri"))
        s["star2"] = mk(self._tone(1319, 0.5, 0.45, 3, "tri"))
        s["buy"] = mk(self._seq([(1568, 0.07), (2093, 0.3)], 0.4, "sine", 4))

    def play(self, name, vol=1.0):
        if not self.ok or self.muted:
            return
        snd = self.sounds.get(name)
        if snd:
            snd.set_volume(max(0.0, min(1.0, vol)))
            snd.play()

    # ------------------------------------------------------------------
    # engine
    # ------------------------------------------------------------------
    def _build_engine(self):
        self.engine_ch = []
        for i in range(self.LEVELS):
            f = 52.0 + i * 17.0
            cycles = max(2, int(round(f * 0.35)) // 2 * 2)     # even number of cycles
            n = int(round(self.rate * cycles / f))
            f = cycles * self.rate / n                          # makes the loop seamless
            samples = []
            for j in range(n):
                t = j / self.rate
                s = 0.0
                for k in range(1, 8):
                    s += math.sin(math.tau * k * f * t + k * 0.7) / (k ** 1.1)
                am = 1.0 + 0.45 * math.sin(math.tau * (f / 2.0) * t)
                samples.append(s * am * 0.2)
            ch = pygame.mixer.Channel(i)
            ch.play(self._make(samples), loops=-1)
            ch.set_volume(0.0)
            self.engine_ch.append(ch)

    def engine(self, rpm, throttle):
        """rpm 0..1 picks the pitch; throttle 0..1 makes it louder."""
        if not self.ok:
            return
        if self.muted:
            self.engine_off()
            return
        self.engine_silent = False
        pos = max(0.0, min(1.0, rpm)) * (self.LEVELS - 1)
        i0 = int(pos)
        frac = pos - i0
        master = 0.28 + 0.3 * throttle
        for i, ch in enumerate(self.engine_ch):
            v = 0.0
            if i == i0:
                v = (1.0 - frac) * master
            elif i == i0 + 1:
                v = frac * master
            ch.set_volume(v)

    def engine_off(self):
        if not self.ok or self.engine_silent:
            return
        self.engine_silent = True
        for ch in self.engine_ch:
            ch.set_volume(0.0)

    # ------------------------------------------------------------------
    # music
    # ------------------------------------------------------------------
    def _build_music(self):
        self.music_ch = pygame.mixer.Channel(self.LEVELS)
        if not MUSIC:
            return
        beat = 60.0 / 118.0
        total = int(self.rate * beat * 16)
        buf = [0.0] * total
        chords = [(110.0, (220.0, 261.63, 329.63)), (87.31, (174.61, 220.0, 261.63)),
                  (130.81, (261.63, 329.63, 392.0)), (98.0, (196.0, 246.94, 293.66))]
        pattern = [0, 1, 2, 1, 0, 1, 2, 1]
        for bar, (root, tones) in enumerate(chords):
            for step in range(8):
                start = int(self.rate * beat * (bar * 4 + step / 2.0))
                note = self._tone(tones[pattern[step]] * 2, beat * 0.5, 0.16, 5, "square")
                self._add(buf, start, note)
                if step % 2 == 1:
                    self._add(buf, start, self._noise(0.04, 0.12, 6, 0.9, bar * 8 + step))
            for b in range(4):
                start = int(self.rate * beat * (bar * 4 + b))
                self._add(buf, start, self._tone(root, beat * 0.95, 0.42, 2.5, "tri"))
                if b % 2 == 0:
                    self._add(buf, start, self._tone(120, 0.14, 0.5, 6, "sine", -300))
        peak = max(1e-6, max(abs(v) for v in buf))
        buf = [v * 0.8 / peak for v in buf]
        self.music = self._make(buf)
        self.music_ch.play(self.music, loops=-1)
        self.music_ch.set_volume(self.music_level)

    @staticmethod
    def _add(buf, start, samples):
        end = min(len(buf), start + len(samples))
        for i in range(start, end):
            buf[i] += samples[i - start]

    def set_music_level(self, level):
        self.music_level = level
        if self.ok and MUSIC:
            self.music_ch.set_volume(0.0 if self.muted else level)

    def toggle_mute(self):
        self.muted = not self.muted
        if not self.ok:
            return self.muted
        if self.muted:
            self.engine_off()
            if MUSIC:
                self.music_ch.set_volume(0.0)
        elif MUSIC:
            self.music_ch.set_volume(self.music_level)
        return self.muted
