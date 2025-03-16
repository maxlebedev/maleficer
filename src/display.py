from enum import IntEnum

import typ

CONSOLE_WIDTH = 1920
CONSOLE_HEIGHT = 1080
TILE_SIZE = 16


PANEL_WIDTH = 27  # 42
# display.BOARD_WIDTH=66 display.BOARD_HEIGHT=67
PANEL_HEIGHT = CONSOLE_HEIGHT // TILE_SIZE

BOARD_HEIGHT = (CONSOLE_HEIGHT // TILE_SIZE) - 1
# TODO: use the one line at the bottom somehow
BOARD_WIDTH = (CONSOLE_WIDTH // TILE_SIZE) - PANEL_WIDTH - PANEL_WIDTH

R_PANEL_START = PANEL_WIDTH + BOARD_WIDTH

class Color:
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    GREEN = (0, 255, 0)
    RED = (255, 0, 0)
    BLUE = (0, 0, 255)
    LGREY = (100, 100, 100)
    DGREY = (50, 50, 50)
    YELLOW = (55, 55, 37)

    CANDLE = (97, 85, 52)
    BAR_FILLED = GREEN
    BAR_EMPTY = RED


class Glyph(IntEnum):
    # ints are all overwritten at asset load time
    NONE = 0
    FLOOR = 3
    WALL = 637
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
}


def darker(rgb: typ.RGB, scale: int) -> typ.RGB:
    red = max(0, rgb[0] + scale)
    blue = max(0, rgb[1] + scale)
    green = max(0, rgb[2] + scale)
    return (red, blue, green)


def brighter(rgb: typ.RGB, scale: int) -> typ.RGB:
    red = min(255, rgb[0] + scale)
    blue = min(255, rgb[1] + scale)
    green = min(255, rgb[2] + scale)
    return (red, blue, green)
