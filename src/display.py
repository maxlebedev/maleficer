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


class Color:
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    GREEN = (0, 255, 0)
    DARK_GREEN = (95, 172, 36)
    RED = (255, 0, 0)
    LIGHT_RED = (223, 80, 80)
    BLOOD_RED = (187, 10, 30)
    BLUE = (0, 0, 255)
    CYAN = (0, 255, 255)
    LCYAN = (186, 225, 255)
    LGREY = (100, 100, 100)
    DGREY = (50, 50, 50)
    YELLOW = (55, 55, 37)
    ORANGE = (255, 128, 0)
    LORANGE = (255, 223, 186)
    MAGENTA = (253, 61, 181)
    BROWN = (94, 44, 4)
    INDIGO = (75, 0, 130)
    CHOCOLATE = (210, 105, 30)
    LEMON = (255, 250, 205)
    BEIGE = (245, 245, 220)

    CANDLE = (97, 85, 52)
    BAR_FILLED = GREEN
    BAR_EMPTY = RED
    # TARGET = (205, 198, 170)  # off-white
    TARGET = (136, 175, 205)  # light cyan
    FLOOR = (70, 70, 70)


class Mood:
    """mood colors, to differentiate the vibes of different levels"""

    blue = {
        (166, 92, 250): 1,
        (114, 92, 250): 2,
        (92, 121, 250): 3,
        (92, 171, 250): 2,
        (92, 221, 250): 1,
    }
    orange = {
        (237, 203, 97): 1,
        (237, 186, 97): 2,
        (237, 165, 97): 3,
        (237, 140, 97): 2,
        (237, 116, 97): 1,
    }
    green = {
        (96, 240, 106): 1,
        (97, 237, 155): 2,
        (97, 237, 202): 3,
        (97, 225, 237): 2,
        (100, 181, 240): 1,
    }
    purple = {
        (164, 96, 240): 1,
        (209, 97, 237): 2,
        (237, 97, 205): 3,
        (237, 97, 121): 2,
        (240, 118, 101): 1,
    }

    @classmethod
    def shuffle(cls):
        choices = [cls.blue, cls.orange, cls.green, cls.purple]
        return random.choice(choices)


class Glyph(IntEnum):
    # ints are all overwritten at asset load time, so import-time uses are discouraged
    NONE = 0
    FLOOR = 3
    WALL = 637
    BWALL = 643
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


@dataclass
class BGImage:
    obj: Image
    x: int
    y: int
    scale: float

# main_menu scale: 0.05
# charselect scale: 0.20


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


def brighter(rgb: typ.RGB, scale: int) -> typ.RGB:
    scale_up = lambda x: min(255, x + scale)
    return tuple(map(scale_up, rgb))  # type: ignore


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
    to_color =chr(tcod.libtcodpy.COLCTRL_FORE_RGB)
    fg = ''.join([chr(c) for c in color])
    from_color = chr(tcod.libtcodpy.COLCTRL_STOP)
    return f"{to_color}{fg}{text}{from_color}"
