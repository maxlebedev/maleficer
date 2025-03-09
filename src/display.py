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

# colors
RGB = tuple[int, int, int]
CELL_RGB = tuple[int, RGB, RGB]

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
LGREY = (100, 100, 100)
DGREY = (50, 50, 50)
YELLOW = (55, 55, 37)


class Glyph:
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


def darker(rgb: RGB, scale):
    red = max(0, rgb[0] + scale)
    blue = max(0, rgb[1] + scale)
    green = max(0, rgb[2] + scale)
    return (red, blue, green)


def brighter(rgb: RGB, scale: int):
    red = min(255, rgb[0] + scale)
    blue = min(255, rgb[1] + scale)
    green = min(255, rgb[2] + scale)
    return (red, blue, green)
