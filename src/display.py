import itertools
import random
import string
from dataclasses import dataclass
from enum import IntEnum

import tcod
from tcod.image import Image

import typ

CONSOLE_WIDTH = 1920
CONSOLE_HEIGHT = 1080
TILE_SIZE = 16
TS_WIDTH = 49
TS_HEIGHT = 22


PANEL_WIDTH = 28
PANEL_IWIDTH = PANEL_WIDTH - 2
# display.BOARD_WIDTH=66 display.BOARD_HEIGHT=67
PANEL_HEIGHT = CONSOLE_HEIGHT // TILE_SIZE
PANEL_IHEIGHT = PANEL_HEIGHT - 2

BOARD_HEIGHT = 64
BOARD_WIDTH = 64


R_PANEL_START = (CONSOLE_WIDTH // TILE_SIZE) - PANEL_WIDTH
CENTER_W = PANEL_WIDTH + (BOARD_WIDTH // 2)
CENTER_H = BOARD_HEIGHT // 2

BOARD_STARTX = PANEL_WIDTH
BOARD_ENDX = R_PANEL_START
BOARD_STARTY = 1
BOARD_ENDY = BOARD_STARTY + BOARD_HEIGHT


def hex_to_rgb(hex: str) -> tuple:
    return tuple(int(hex[i : i + 2], 16) for i in (0, 2, 4))


class Color:
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    GREEN = hex_to_rgb("55b33b")  # (0, 255, 0)
    DARK_GREEN = hex_to_rgb("179c43")  # (95, 172, 36)
    RED = hex_to_rgb("f53141")  # (255, 0 0)
    LIGHT_RED = hex_to_rgb("ff7070")  # (223, 80, 80)
    BLOOD_RED = hex_to_rgb("c40c2e")  # (187, 10, 30)
    BLUE = hex_to_rgb("1c75bd")  # (0, 0, 255)
    LCYAN = hex_to_rgb("49c2f2")  # (0, 255, 255)
    CYAN = hex_to_rgb("25acf5")  # (186, 225, 255)
    LGREY = hex_to_rgb("a69a9c")  # (100, 100, 100)
    DGREY = hex_to_rgb("807980")  # (50, 50, 50)
    YELLOW = hex_to_rgb("fad937")  # (55, 55, 37)
    ORANGE = hex_to_rgb("f58122")  # (255, 128, 0)
    MAGENTA = hex_to_rgb("773bbf")  # (253, 61, 181)
    INDIGO = hex_to_rgb("4e278c")  # (75, 0, 130)
    BROWN = hex_to_rgb("7a5e37")  # (94, 44, 4)
    CHOCOLATE = hex_to_rgb("ad6a45")  # (210, 105, 30)
    BEIGE = hex_to_rgb("f2f2da")  # (245, 245, 220)

    CANDLE = (97, 85, 52)
    FLOOR = (70, 70, 70)
    BAR_FILLED = GREEN
    BAR_EMPTY = RED
    # TARGET = (205, 198, 170)  # off-white
    TARGET = LCYAN  # (136, 175, 205)  # light cyan


class Mood:
    """mood colors, to differentiate the vibes of different maps"""

    blue = {
        hex_to_rgb("49c2f2"): 1,
        hex_to_rgb("25acf5"): 2,
        hex_to_rgb("1793e6"): 3,
        hex_to_rgb("1c75bd"): 2,
        hex_to_rgb("195ba6"): 1,
    }
    orange = {
        hex_to_rgb("faa032"): 1,
        hex_to_rgb("f58122"): 2,
        hex_to_rgb("f2621f"): 3,
        hex_to_rgb("db4b16"): 2,
        hex_to_rgb("9e4c4c"): 1,
    }
    green = {
        hex_to_rgb("94bf30"): 1,
        hex_to_rgb("55b33b"): 2,
        hex_to_rgb("179c43"): 3,
        hex_to_rgb("068051"): 2,
        hex_to_rgb("116061"): 1,
    }
    purple = {
        hex_to_rgb("e29bfa"): 1,
        hex_to_rgb("ca7ef2"): 2,
        hex_to_rgb("a35dd9"): 3,
        hex_to_rgb("773bbf"): 2,
        hex_to_rgb("4e278c"): 1,
    }
    earthy = {
        hex_to_rgb("b58c7f"): 1,
        hex_to_rgb("9e7767"): 2,
        hex_to_rgb("875d58"): 3,
        hex_to_rgb("6e4250"): 2,
        hex_to_rgb("472e3e"): 1,
    }

    @classmethod
    def shuffle(cls):
        choices = [cls.blue, cls.orange, cls.green, cls.purple, cls.earthy]
        return random.choice(choices)


class Glyph(IntEnum):
    # ints are all overwritten at asset load time, so import-time uses are discouraged
    NONE = 0
    FLOOR = 3
    WALL1 = 637
    WALL2 = 843
    BWALL1 = 643
    BWALL2 = 893
    PLAYER = 73
    BEATRICE = 75
    FRAME1 = 947
    FRAME2 = 948
    FRAME3 = 949
    FRAME4 = 996
    FRAME5 = 997
    FRAME6 = 998
    FRAME7 = 1045
    FRAME8 = 1046
    FRAME9 = 1047
    BAT = 418
    SKELETON = 323
    CROSSHAIR = 711
    POTION = 581
    TRAP = 737
    SCROLL = 768
    STAIRS = 297
    WARLOCK = 80
    BOMB = 486
    GOBLIN = 127
    MAGIC_MISSILE = 618
    FLAME = 505
    CYCLOPS = 465


def get_tile_glyphs():
    return [Glyph.FLOOR, Glyph.WALL1, Glyph.WALL2, Glyph.BWALL1, Glyph.BWALL2]


letter_map = {
    "0": 868,
    "1": 869,
    "2": 870,
    "3": 871,
    "4": 872,
    "5": 873,
    "6": 874,
    "7": 875,
    "8": 876,
    "9": 877,
    ":": 878,
    ".": 879,
    "A": 917,
    "B": 918,
    "C": 919,
    "D": 920,
    "E": 921,
    "F": 922,
    "G": 923,
    "H": 924,
    "I": 925,
    "J": 926,
    "K": 927,
    "L": 928,
    "M": 929,
    "N": 966,
    "O": 967,
    "P": 968,
    "Q": 969,
    "R": 970,
    "S": 971,
    "T": 972,
    "U": 973,
    "V": 974,
    "W": 975,
    "X": 976,
    "Y": 977,
    "Z": 978,
    "a": 917,
    "b": 918,
    "c": 919,
    "d": 920,
    "e": 921,
    "f": 922,
    "g": 923,
    "h": 924,
    "i": 925,
    "j": 926,
    "k": 927,
    "l": 928,
    "m": 929,
    "n": 966,
    "o": 967,
    "p": 968,
    "q": 969,
    "r": 970,
    "s": 971,
    "t": 972,
    "u": 973,
    "v": 974,
    "w": 975,
    "x": 976,
    "y": 977,
    "z": 978,
    "/": 1013,
    "-": 1017,
}


def _idx_to_point(x, y):
    return (x % y, x // y)


def linear_to_srgb(c: int) -> float:
    """https://en.wikipedia.org/wiki/SRGB transfer function"""
    c_norm = c / 255.0

    if c_norm <= 0.0031308:
        return 0.03928 * c_norm
    return ((c_norm + 0.055) / 1.055) ** 2.4


def srgb_to_linear(c: float) -> int:
    c_norm = max(0, min(1, c)) ** 0.41666
    return round(max(0, min(255, c_norm * 255)))


def brighter(rgb: typ.RGB, scale: int) -> typ.RGB:
    scale_up = lambda x: min(255, x + scale)
    return tuple(map(scale_up, rgb))  # type: ignore


def darker(color: typ.RGB, factor: float = 0.75) -> typ.RGB:
    """Convert to perceptual space, darken, convert back"""
    linear_channels = [linear_to_srgb(channel) for channel in color]
    darker_linear = [channel * factor for channel in linear_channels]
    return tuple(srgb_to_linear(channel) for channel in darker_linear)  # type: ignore


def load_tileset(atlas_path: str, width: int, height: int) -> tcod.tileset.Tileset:
    font_atlas = "assets/Cheepicus_8x8x2.png"
    font_ts = tcod.tileset.load_tilesheet(
        font_atlas, 16, 16, tcod.tileset.CHARMAP_CP437
    )
    tileset = tcod.tileset.load_tilesheet(atlas_path, width, height, None)

    for letter in string.printable:
        tile = font_ts.get_tile(ord(letter))
        tileset.set_tile(ord(letter), tile)

    for char in "┌─┐│ └─┘├┤":
        tile = font_ts.get_tile(ord(char))
        tileset.set_tile(ord(char), tile)

    codepath = itertools.count(ord("z") + 1)
    for glyph in Glyph:
        xx, yy = _idx_to_point(glyph.value, width)
        tileset.remap(next(codepath), xx, yy)

    return tileset


def remap_glyphs():
    codepath = itertools.count(ord("z") + 1)
    glyph_map = {glyph.name: next(codepath) for glyph in Glyph}

    return IntEnum("Glyph", glyph_map)


def blit_image(console, img, scale):
    args = {"x": CENTER_W, "y": CENTER_H, "bg_blend": 1, "angle": 0}
    img.blit(console, scale_x=scale, scale_y=scale, **args)


def write_rgbs(console, cell_rgbs):
    startx, endx = (BOARD_STARTX, BOARD_ENDX)
    starty, endy = (BOARD_STARTY, BOARD_ENDY)
    console.rgb[startx:endx, starty:endy] = cell_rgbs
    # TODO if the magnification changes, the above line breaks


def colored_text(text: str, color: typ.RGB) -> str:
    to_color = chr(tcod.libtcodpy.COLCTRL_FORE_RGB)
    fg = "".join([chr(c) for c in color])
    from_color = chr(tcod.libtcodpy.COLCTRL_STOP)
    return f"{to_color}{fg}{text}{from_color}"
