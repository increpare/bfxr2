#!/usr/bin/env python3
"""Draws the synth logos shown behind the waveform display (img/logo_<synth>.png).

Each logo is one ink colour on transparent. The synth's display name runs up
the right-hand edge in the Bfxr logo's outline lettering, and a little scene is
drawn down the two sides. The waveform is drawn over the top, down the middle
of the panel, so scenes keep the middle clear and treat the waveform as a prop
(a mast, a string, a tree trunk...). logo_bfxr.png is hand-drawn and is not
generated here.

    python3 tools/logos/make_logos.py            # writes img/logo_*.png
    python3 tools/logos/make_logos.py sheet.png  # also writes a contact sheet
"""
import math
import os
import sys

from PIL import Image

W, H = 113, 200          # display canvas size (js/Tab.js)
INK = (231, 209, 167)    # same ink as logo_bfxr.png
PANEL = (204, 189, 161)  # --panel-background-color, for the contact sheet
WAVE = (102, 57, 49)     # waveform colour, for the contact sheet
TEXT_SCALE = 3           # screen pixels per lettering cell, as in logo_bfxr.png
RIGHT, BOTTOM = 111, 198 # where the Bfxr wordmark sits
CELL = 2                 # screen pixels per scene cell
GW, GH = W // CELL, H // CELL   # scene grid: 56 x 100, waveform at x = 28

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")


# ---------------------------------------------------------------- lettering
# Glyphs are lists of (row, repeat). Lowercase is 10 cells tall, capitals 14.

def g(*rows):
    out = []
    for r in rows:
        if isinstance(r, tuple):
            out += [r[0]] * r[1]
        else:
            out.append(r)
    return out

LOWER = {
    "a": g(".###.", "#...#", ("....#", 2), ".####", ("#...#", 4), ".####"),
    "b": g(("#....", 4), "####.", ("#...#", 4), "####."),
    "c": g(".###.", "#...#", ("#....", 6), "#...#", ".###."),
    "d": g(("....#", 4), ".####", ("#...#", 4), ".####"),
    "e": g(".###.", ("#...#", 3), "#####", ("#....", 3), "#...#", ".###."),
    "f": g(".####", ("#....", 3), "####.", ("#....", 5)),
    "g": g(".####", ("#...#", 4), ".####", ("....#", 2), "#...#", ".###."),
    "h": g(("#....", 4), "####.", ("#...#", 5)),
    "i": g("#", ".", ("#", 8)),
    "k": g(("#....", 3), "#...#", "#..#.", "###..", "#..#.", ("#...#", 3)),
    "l": g(("#.", 9), ".#"),
    "m": g("###.##.", ("#..#..#", 9)),
    "n": g("#.##.", "##..#", ("#...#", 8)),
    "o": g(".###.", ("#...#", 8), ".###."),
    "p": g("####.", ("#...#", 4), "####.", ("#....", 4)),
    "q": g(".####", ("#...#", 4), ".####", ("....#", 4)),
    "r": g("#.##.", "##..#", ("#....", 8)),
    "s": g(".###.", "#...#", ("#....", 2), ".###.", ("....#", 3), "#...#", ".###."),
    "t": g((".#...", 3), "####.", (".#...", 4), ".#..#", "..##."),
    "u": g(("#...#", 8), "#..##", ".##.#"),
    "w": g(("#..#..#", 9), ".##.##."),
    "x": g(("#...#", 3), ".#.#.", ("..#..", 2), ".#.#.", ("#...#", 3)),
    "y": g(("#...#", 5), ".####", ("....#", 2), "#...#", ".###."),
}

UPPER = {
    "B": g("#######.", ("#......#", 5), "#######.", ("#......#", 6), "#######."),
    "C": g(".######.", "#......#", ("#.......", 10), "#......#", ".######."),
    "F": g("########", ("#.......", 5), "######..", ("#.......", 7)),
    "G": g(".######.", "#......#", ("#.......", 4), "#...####", ("#......#", 6), ".######."),
    "J": g("..######", ("......#.", 9), ("#.....#.", 3), ".#####.."),
    "M": g("#.......#", "##.....##", "#.#...#.#", "#..#.#..#", "#...#...#", ("#.......#", 9)),
    "P": g("#######.", ("#......#", 6), "#######.", ("#.......", 6)),
    "R": g("#######.", ("#......#", 5), "#######.", "#..#....", "#...#...", "#....#..",
           "#.....#.", ("#......#", 3)),
    "S": g(".######.", "#......#", ("#.......", 4), ".######.", (".......#", 5),
           "#......#", ".######."),
    "T": g("#########", ("....#....", 13)),
    "W": g(("#...#...#", 10), "#..#.#..#", "#.#...#.#", "##.....##", "#.......#"),
    "Z": g("########", ".......#", ("......#.", 2), (".....#..", 2), "....#...",
           ("...#....", 2), ("..#.....", 2), ".#......", "#.......", "########"),
}


def wordmark(name):
    """The name as a set of cells, reading left to right, baseline at y=13."""
    cells, x = set(), 0
    for ch in name:
        glyph = UPPER[ch] if ch in UPPER else LOWER[ch]
        top = 14 - len(glyph)
        for y, row in enumerate(glyph):
            for dx, c in enumerate(row):
                if c == "#":
                    cells.add((x + dx, top + y))
        x += len(glyph[0]) + 1
    return cells


# ------------------------------------------------------------------- scenes

class Pic:
    """The scene grid, with a few drawing helpers. Off-grid cells are ignored."""

    def __init__(self):
        self.on = set()

    def px(self, *pts, on=1):
        for x, y in pts:
            if on and 0 <= x < GW and 0 <= y < GH:
                self.on.add((x, y))
            elif not on:
                self.on.discard((x, y))

    def rect(self, x, y, w, h, fill=True, on=1):
        self.px(*[(i, j) for i in range(x, x + w) for j in range(y, y + h)
                  if fill or i in (x, x + w - 1) or j in (y, y + h - 1)], on=on)

    def line(self, *pts, on=1):
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            n = max(abs(x1 - x0), abs(y1 - y0), 1)
            self.px(*[(round(x0 + (x1 - x0) * i / n), round(y0 + (y1 - y0) * i / n))
                      for i in range(n + 1)], on=on)

    def dots(self, *pts, step=3):
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            n = max(abs(x1 - x0), abs(y1 - y0), 1)
            self.px(*[(round(x0 + (x1 - x0) * i / n), round(y0 + (y1 - y0) * i / n))
                      for i in range(0, n + 1, step)])

    @staticmethod
    def _disc(x, y, w, h=None):
        h = h or w
        cx, cy = x + w / 2, y + h / 2
        return {(i, j) for i in range(x, x + w) for j in range(y, y + h)
                if ((i + .5 - cx) / (w / 2)) ** 2 + ((j + .5 - cy) / (h / 2)) ** 2 <= 1.0}

    @staticmethod
    def _edge(s):
        return [p for p in s if any((p[0] + a, p[1] + b) not in s
                                    for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)))]

    def disc(self, x, y, w, h=None, on=1):
        self.px(*self._disc(x, y, w, h), on=on)

    def ring(self, x, y, w, h=None, keep=None):
        self.px(*[p for p in self._edge(self._disc(x, y, w, h)) if not keep or keep(*p)])

    def blob(self, *discs):
        """Outline of several overlapping discs."""
        s = set()
        for d in discs:
            s |= self._disc(*d)
        self.px(*self._edge(s))

    def art(self, x, y, rows, flip=False):
        """Stamp ASCII art: '#' sets, '-' clears, anything else leaves alone."""
        for j, row in enumerate(rows):
            if flip:
                row = row[::-1]
            for i, c in enumerate(row):
                if c in "#-":
                    self.px((x + i, y + j), on=c == "#")

    def shift_rows(self, y0, y1, dx):
        moved = {(x, y) for x, y in self.on if y0 <= y < y1}
        self.on -= moved
        self.px(*[(x + dx, y) for x, y in moved])


NOTE = ["..##", "..#.", "..#.", "###.", "###."]
SPARKLE = ["..#..", "..#..", "##.##", "..#..", "..#.."]
BELL = [
    "......##......",
    ".....#..#.....",
    "....######....",
    "...#......#...",
    "..#........#..",
    "..#........#..",
    "..#..#..#..#..",
    "..#..#..#..#..",
    "..#........#..",
    "..#........#..",
    ".#..........#.",
    "#............#",
    "##############",
    ".....####.....",
    "......##......",
]
BIRD = [
    "......######........",
    ".....########.......",
    "....##########......",
    "##.####-#######...##",
    "..#####-########.###",
    "##.#################",
    "....###############.",
    "....##############..",
    ".....###########....",
    "......#########.....",
    ".......#######......",
    "........#..#........",
    "........#..#........",
    ".......##.##........",
]
PAPER = [
    "#########....",
    "#.......##...",
    "#.......#.#..",
    "#.......#..#.",
    "#.......#####",
    "#...........#",
    "#..#######..#",
    "#...........#",
    "#..#######..#",
    "#...........#",
    "#..#####....#",
    "#...........#",
    "#...........#",
    "#############",
]
SCRAP = ["#####..", "#...##.", "#...###", "#.....#", "#.###.#", "#.....#", "#.....#", "#######"]
SLIME = [
    "......####.........",
    "....########.......",
    "...##########......",
    "..############.....",
    "..############.....",
    ".###-####-#####....",
    ".###-####-#####....",
    "################...",
    "#####-##-#######...",
    "######--########...",
    "################...",
    "#################..",
    "##################.",
    ".################..",
]
COG = [
    ".......###.......",
    "..##...###...##..",
    ".####.#####.####.",
    ".###############.",
    "..#############..",
    "...####---####...",
    "..####-----####..",
    "#####---#---#####",
    "#####--###--#####",
    "#####---#---#####",
    "..####-----####..",
    "...####---####...",
    "..#############..",
    ".###############.",
    ".####.#####.####.",
    "..##...###...##..",
    ".......###.......",
]
PAW = [".#.#.", ".#.#.", ".....", ".###.", "#####", ".###."]
SUB = [
    "......##.....",
    "......#......",
    "..########...",
    ".##########.#",
    "###-###-#####",
    ".##########.#",
    "..########...",
]


def footsteppr(p):
    # boot prints walking up the side of the waveform
    for i, y in enumerate((80, 62, 44, 26, 8)):
        x = 2 if i % 2 == 0 else 11
        p.disc(x, y, 7, 10)
        p.rect(x + 1, y + 11, 5, 4)
        p.px((x + 1, y + 14), (x + 5, y + 14), on=0)

def mixr(p):
    # two faders; the waveform makes a third
    for x, y0, y1, knob in ((10, 14, 84, 56), (46, 5, 39, 14)):
        p.rect(x, y0, 1, y1 - y0)
        p.rect(x - 2, y0 - 1, 5, 1); p.rect(x - 2, y1, 5, 1)
        for y in range(y0 + 5, y1 - 2, 8):
            p.rect(x + 4, y, 2, 1)
        p.rect(x - 3, knob, 7, 5, on=0)
        p.rect(x - 3, knob, 7, 5, fill=False)
        p.rect(x - 1, knob + 2, 3, 1)

def transfxr(p):
    # a square turning into a circle on the way down
    p.rect(4, 8, 11, 11, fill=False)
    p.art(4, 37, ["..#######..", ".#.......#.", "#.........#"] + ["#.........#"] * 5 +
          ["#.........#", ".#.......#.", "..#######.."])
    p.ring(4, 66, 11)
    for y in (24, 53):
        p.px((9, y), (9, y + 2))
        p.art(7, y + 4, ["#...#", ".#.#.", "..#.."])
    p.art(44, 6, SPARKLE)

def jinglr(p):
    # bells hung either side
    for x, y in ((3, 22), (40, 10)):
        p.rect(x + 6, 0, 1, y)
        p.art(x, y, BELL)
    p.art(6, 48, NOTE); p.art(12, 64, NOTE); p.art(3, 80, NOTE)
    p.art(1, 42, SPARKLE); p.art(13, 82, SPARKLE); p.art(47, 30, SPARKLE)

def pluckr(p):
    # the waveform is the string: headstock above, bridge below, pick alongside
    p.rect(21, 1, 15, 7, fill=False)
    for y in (2, 5):
        p.rect(18, y, 2, 2); p.rect(37, y, 2, 2)
    p.rect(22, 10, 13, 1)
    p.ring(18, 60, 20)
    p.rect(18, 93, 15, 4, fill=False)
    p.art(3, 31, [".####........", "#######......", "#########....", "###########..",
                  "############.", "#############", "############.", "###########..",
                  "#########....", "#######......", ".####........"])
    p.rect(5, 35, 2, 3, on=0)
    p.px((18, 31), (20, 29), (18, 41), (20, 43))

def choirr(p):
    # singers facing in from both sides
    for x, y in ((5, 20), (8, 52), (42, 12), (43, 36)):
        p.ring(x, y, 9)
        p.px((x + 2, y + 3), (x + 6, y + 3))
        p.art(x + 3, y + 4, [".#.", "#.#", ".#."])
        p.art(x, y + 9, ["..#####..", ".#.....#.", "#.......#", "#########"])
    p.art(2, 8, NOTE); p.art(14, 40, NOTE); p.art(3, 74, NOTE); p.art(38, 2, NOTE)

def crittr(p):
    # a beast peering round the waveform, which makes a fine tongue
    for x, flip in ((6, False), (38, True)):
        p.art(x, 2, [".....##.....", "....####....", "...######...", "..########..",
                     ".####..####.", "####....####"], flip)
        p.ring(x + 1, 12, 10)
        p.disc(x + 4, 15, 4)
    p.line((4, 28), (6, 31), (20, 31)); p.line((51, 28), (49, 31), (36, 31))
    p.art(13, 32, ["#####", "#####", ".###.", ".###.", "..#.."])
    p.art(38, 32, ["#####", "#####", ".###.", ".###.", "..#.."])
    p.art(4, 62, PAW); p.art(12, 74, PAW); p.art(5, 86, PAW)

def birdr(p):
    # the waveform is a tree trunk
    p.rect(4, 52, 24, 2)
    p.line((9, 52), (6, 48)); p.px((5, 47), (4, 47), (5, 46))
    p.art(0, 38, BIRD)
    p.rect(29, 30, 21, 2)
    p.line((45, 30), (48, 26)); p.px((49, 25), (50, 25), (49, 24))
    p.art(37, 25, ["..#..#...", ".###.###.", "#########", ".#######.", "..#####.."])
    p.art(3, 26, NOTE); p.art(11, 18, NOTE)

def swarmr(p):
    # a spiral of tiny flyers circling the waveform
    for k in range(40):
        a = k * 0.83
        x, y = round(28 + 22 * math.cos(a)) - 2, 2 + round(k * 2.4)
        if abs(x + 2 - 28) > 10 and not (x > 30 and y > 28):
            p.art(x, y, ["#...#", ".#.#.", "..#.."] if k % 3 else ["#.#", ".#."])
    p.px((12, 6), (7, 22), (15, 37), (4, 51), (13, 66), (8, 80), (16, 93), (44, 5),
         (50, 14), (41, 27))

def clonkr(p):
    # a mallet striking the waveform, which rings
    p.rect(13, 34, 7, 10)
    p.px((13, 34), (19, 34), (13, 43), (19, 43), on=0)
    p.line((12, 39), (1, 52)); p.line((12, 40), (2, 52))
    p.px((16, 30), (18, 28), (16, 47), (18, 49))
    for d in (20, 28, 36):
        p.ring(28 - d // 2, 37 - d // 2, d, keep=lambda x, y: x > 36 and abs(y - 37) < (x - 28) * .8)
    p.art(7, 68, ["#...#"] * 6 + [".###.", "..#..", "..#..", "..#..", "..#.."])
    p.px((4, 69), (4, 72), (14, 69), (14, 72))

def bouncr(p):
    # a ball bonking off the waveform
    p.dots((3, 6), (19, 30))
    p.art(17, 31, ["#.#.#", ".....", "#...#", ".....", "#.#.#"])
    p.dots((17, 37), (6, 56))
    p.disc(2, 58, 11)
    p.px((5, 62), (9, 62), on=0)
    p.rect(5, 65, 5, 1, on=0)
    p.dots((38, 24), (42, 14), step=2)
    p.disc(42, 4, 9)
    p.px((45, 7), (48, 7), on=0); p.rect(45, 9, 4, 1, on=0)
    p.dots((8, 74), (18, 92))

def fractr(p):
    # cracks spreading out from the waveform
    p.line((20, 20), (14, 24), (16, 30), (8, 34), (10, 40), (2, 44))
    p.line((16, 30), (13, 37))
    p.line((20, 58), (13, 56), (11, 64), (4, 62), (1, 70))
    p.line((11, 64), (14, 70))
    p.line((36, 12), (42, 8), (44, 16), (52, 12), (55, 18))
    p.line((36, 24), (41, 27), (46, 23))
    for x, y in ((4, 82), (13, 89), (8, 76)):
        p.art(x, y, [".##.", "####", "###.", ".#.."])

def boomr(p):
    # mushroom cloud on top of the waveform, bomb below
    p.blob((2, 8, 13), (10, 2, 14), (21, 1, 14), (33, 2, 14), (42, 8, 12))
    p.px((9, 10), (10, 9), (11, 9), (37, 8), (38, 8), (39, 9))
    p.disc(2, 72, 15)
    p.px((6, 77), (6, 78), (11, 77), (11, 78), on=0)
    p.rect(7, 81, 4, 1, on=0)
    p.rect(7, 70, 5, 2)
    p.line((9, 69), (9, 67), (11, 65), (13, 65), (15, 67))
    p.art(14, 66, [".#.#.", "..#..", "##.##", "..#..", ".#.#."])
    p.px((16, 68), on=0)

def rustlr(p):
    # loose sheets fluttering down
    p.art(3, 10, PAPER); p.art(5, 62, PAPER); p.art(40, 6, PAPER)
    p.art(10, 38, SCRAP); p.art(45, 24, SCRAP); p.art(2, 86, SCRAP)
    for x, y in ((8, 2), (16, 30), (11, 54)):
        p.art(x, y, ["#..", ".#.", "#..", ".#.", "#.."])

def squishr(p):
    # goo dripping from the top; a happy slime at the bottom
    p.rect(0, 0, GW, 3)
    for x, w, n in ((3, 4, 14), (10, 3, 6), (15, 4, 22), (38, 4, 12), (45, 3, 20), (50, 4, 8)):
        p.rect(x, 3, w, n)
        p.disc(x, 3 + n - w // 2, w)
    p.art(15, 32, [".##.", "####", "####", ".##."])
    p.art(45, 29, [".#.", "###", ".#."])
    p.art(1, 80, SLIME)
    p.ring(14, 70, 5); p.ring(7, 73, 3)

def machinr(p):
    # gears turning against the waveform
    p.art(1, 20, COG); p.art(3, 37, COG); p.art(38, 8, COG)
    for x, y in ((6, 64), (44, 29), (10, 80)):
        p.ring(x, y, 7); p.rect(x + 2, y + 3, 3, 1)

def breathr(p):
    # someone blowing across the waveform
    p.ring(2, 18, 15)
    p.rect(5, 24, 3, 1); p.rect(10, 24, 3, 1)
    p.art(14, 26, ["-#", "#-", "-#"])
    p.ring(18, 26, 3)
    p.ring(37, 22, 5); p.ring(41, 12, 8); p.ring(46, 2, 9)
    p.ring(4, 60, 6); p.ring(11, 69, 4); p.ring(16, 76, 3)

def whooshr(p):
    # gusts streaming past
    def gust(x, y, n, down=False, flip=False):
        rows = [" " * (n - 5) + ".###.", " " * (n - 5) + "#...#", " " * (n - 5) + "....#",
                "#" * (n - 2) + ".."]
        p.art(x, y - 3 if not down else y, rows[::-1] if down else rows, flip)
    gust(1, 20, 19); p.rect(5, 26, 13, 1)
    gust(2, 48, 17, down=True); p.rect(1, 44, 12, 1)
    gust(1, 74, 19); p.rect(6, 80, 12, 1); p.rect(2, 90, 15, 1)
    gust(37, 10, 18); p.rect(38, 16, 12, 1)
    gust(37, 28, 16, down=True)

def signlr(p):
    # the waveform is a radio mast
    for d in (24, 36, 48):
        p.ring(28 - d // 2, 16 - d // 2, d,
               keep=lambda x, y: abs(x - 28) > 8 and abs(y - 16) < abs(x - 28) * .8)
    p.line((20, 62), (3, 96)); p.line((20, 78), (11, 96))
    p.line((16, 70), (20, 70)); p.line((9, 84), (20, 84))
    p.rect(1, 97, 21, 1)
    p.art(2, 50, ["#.###.#.#.###"])

def riftr(p):
    # sonar rings spreading from the waveform, and who they found
    for d in (14, 28, 44):
        p.ring(28 - d // 2, 27 - d // 2, d)
    p.disc(9, 20, 3)
    p.px((8, 18), (12, 18), (8, 24), (12, 24))
    p.art(3, 76, SUB)
    p.ring(17, 71, 3); p.px((19, 68), (17, 66))

def zappr(p):
    # the waveform is the arc
    p.line((15, 16), (18, 16), (13, 30), (19, 30), (6, 52), (10, 34), (5, 34), (15, 16))
    for y in range(17, 52):
        xs = [x for x, yy in p.on if yy == y and x < 22]
        if xs:
            p.rect(min(xs), y, max(xs) - min(xs) + 1, 1)
    p.line((46, 6), (50, 6), (47, 13), (51, 13), (41, 28), (44, 17), (40, 17), (46, 6))
    for y in range(7, 28):
        xs = [x for x, yy in p.on if yy == y and x > 34]
        if xs:
            p.rect(min(xs), y, max(xs) - min(xs) + 1, 1)
    p.line((20, 64), (15, 62), (12, 68), (6, 65), (3, 71))
    p.line((20, 82), (14, 86), (10, 82), (4, 88))
    p.px((2, 8), (4, 10), (20, 56), (1, 60), (17, 92), (8, 94), (38, 34), (53, 22))

def glitchr(p):
    # a face and its torn scanlines
    p.disc(2, 20, 15)
    p.rect(6, 24, 2, 3, on=0); p.rect(11, 24, 2, 3, on=0)
    p.art(5, 29, ["-.......-", "-.......-", ".-------."])
    p.shift_rows(23, 25, 3)
    p.shift_rows(28, 30, -2)
    p.shift_rows(32, 33, 2)
    for x, y, w, h in ((1, 48, 12, 2), (8, 52, 10, 1), (0, 60, 6, 2), (10, 64, 9, 2),
                       (3, 72, 14, 1), (1, 80, 8, 3), (12, 86, 7, 1), (2, 92, 16, 2),
                       (40, 5, 14, 2), (37, 11, 8, 1), (46, 17, 9, 2), (38, 25, 12, 1),
                       (3, 6, 10, 1), (9, 10, 9, 2)):
        p.rect(x, y, w, h)


# engine name -> (display name, scene). Keep names in step with
# SYNTH_DISPLAY_NAMES in js/globals.js.
LOGOS = {
    "Footsteppr": ("Footsteppr", footsteppr),
    "Mixr": ("Mixfxr", mixr),
    "Transfxr": ("Transfxr", transfxr),
    "Jinglr": ("Jingles", jinglr),
    "Pluckr": ("Plucked", pluckr),
    "Choirr": ("Choir", choirr),
    "Crittr": ("Beasts", crittr),
    "Birdr": ("Bird", birdr),
    "Swarmr": ("Swarms", swarmr),
    "Clonkr": ("Tangs", clonkr),
    "Bouncr": ("Bonks", bouncr),
    "Fractr": ("Cracker", fractr),
    "Boomr": ("Boomer", boomr),
    "Rustlr": ("Rustler", rustlr),
    "Squishr": ("Squishy", squishr),
    "Machinr": ("Motors", machinr),
    "Breathr": ("Breath", breathr),
    "Whooshr": ("Whoosh", whooshr),
    "Signlr": ("Signal", signlr),
    "Riftr": ("Sonar", riftr),
    "Zappr": ("Zapper", zappr),
    "Glitchr": ("Glitches", glitchr),
}


def render(display_name, draw):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    text = set()
    for x, y in wordmark(display_name):      # rotate to read bottom-to-top
        x0, y0 = RIGHT - (14 - y) * TEXT_SCALE, BOTTOM - (x + 1) * TEXT_SCALE
        text |= {(x0 + i, y0 + j) for i in range(TEXT_SCALE) for j in range(TEXT_SCALE)}
    assert min(y for _, y in text) >= 2, display_name + " is too long"

    # Keep the scene off the lettering.
    top = min(y for _, y in text)
    cap = min(y for x, y in text if x < RIGHT - 10 * TEXT_SCALE)
    pic = Pic()
    draw(pic)
    for cx, cy in pic.on:
        x, y = cx * CELL, cy * CELL
        if (x + CELL > RIGHT - 10 * TEXT_SCALE - 3 and y + CELL > top - 3) or \
           (x + CELL > RIGHT - 14 * TEXT_SCALE - 3 and y + CELL > cap - 3):
            print("%s: scene cell (%d, %d) runs into the name" % (display_name, cx, cy))
            continue
        for i in range(CELL):
            for j in range(CELL):
                im.putpixel((x + i, y + j), INK + (255,))
    for xy in text:
        im.putpixel(xy, INK + (255,))
    return im


def contact_sheet(tiles, path, waveform):
    cols, pad = 8, 4
    rows = -(-len(tiles) // cols)
    sheet = Image.new("RGB", (cols * (W + pad) + pad, rows * (H + pad) + pad), (92, 87, 76))
    for i, t in enumerate(tiles):
        cell = Image.new("RGB", (W, H), PANEL)
        cell.paste(t, (0, 0), t)
        if waveform:                         # a stand-in decaying blip
            for y in range(2, H - 2):
                half = round(1 + 16 * ((y / H) ** 2) * (.75 + .25 * math.sin(y * 1.7 + i)))
                for x in range(W // 2 - half, W // 2 + half + 1):
                    cell.putpixel((x, y), WAVE)
        sheet.paste(cell, (pad + (i % cols) * (W + pad), pad + (i // cols) * (H + pad)))
    sheet.resize((sheet.width * 2, sheet.height * 2), Image.NEAREST).save(path)


def main():
    logos = {}
    for engine, (display_name, draw) in LOGOS.items():
        logos[engine] = render(display_name, draw)
        logos[engine].save(os.path.join(ROOT, "img", "logo_%s.png" % engine.lower()))

    if len(sys.argv) > 1:
        tiles = [Image.open(os.path.join(ROOT, "img", "logo_bfxr.png")).convert("RGBA")]
        tiles += list(logos.values())
        contact_sheet(tiles, sys.argv[1], False)
        contact_sheet(tiles, sys.argv[1].replace(".png", "_waveform.png"), True)


if __name__ == "__main__":
    main()
