import itertools
import string
from enum import IntEnum

import tcod

import typ

CONSOLE_WIDTH = 1920
CONSOLE_HEIGHT = 1080
TILE_SIZE = 16
TS_WIDTH = 49
TS_HEIGHT = 22


PANEL_WIDTH = 27  # 42
# display.BOARD_WIDTH=66 display.BOARD_HEIGHT=67
PANEL_HEIGHT = CONSOLE_HEIGHT // TILE_SIZE

BOARD_HEIGHT = CONSOLE_HEIGHT // TILE_SIZE
BOARD_WIDTH = (CONSOLE_WIDTH // TILE_SIZE) - PANEL_WIDTH - PANEL_WIDTH

R_PANEL_START = PANEL_WIDTH + BOARD_WIDTH


class Color:
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    GREEN = (0, 255, 0)
    DARK_GREEN = (95, 172, 36)
    RED = (255, 0, 0)
    BLUE = (0, 0, 255)
    LGREY = (100, 100, 100)
    DGREY = (50, 50, 50)
    YELLOW = (55, 55, 37)
    MAGENTA = (253, 61, 181)
    BLOOD_RED = (187, 10, 30)
    BROWN = (94, 44, 4)
    INDIGO = (75, 0, 130)
    LIGHT_RED = (223, 80, 80)

    CANDLE = (97, 85, 52)
    BAR_FILLED = GREEN
    BAR_EMPTY = RED
    TARGET = RED
    FLOOR = (70, 70, 70)


class Glyph(IntEnum):
    # ints are all overwritten at asset load time, so import-time uses are discouraged
    NONE = 0
    FLOOR = 3
    WALL = 637
    BWALL = 643
    PLAYER = 73
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

    codepath = itertools.count(ord("z") + 1)
    for glyph in Glyph:
        xx, yy = _idx_to_point(glyph.value, width)
        tileset.remap(next(codepath), xx, yy)

    return tileset


def remap_glyphs():
    codepath = itertools.count(ord("z") + 1)
    glyph_map = {glyph.name: next(codepath) for glyph in Glyph}

    return IntEnum("Glyph", glyph_map)
