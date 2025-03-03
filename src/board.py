# do we store info about the board size here?
import components as cmp
import esper
import display
from functools import partial


class Board:
    def make_tile(self, x, y, glyph, color):
        visible_cmp = cmp.Visible(glyph=glyph, color=color)
        tile = esper.create_entity(cmp.Tile(), cmp.Position(x,y), visible_cmp )
        # walls are #visible #blocking
        return tile

    def __init__(self):
        self.entities = []
        self.board_size = display.BOARD_WIDTH*display.BOARD_HEIGHT
        make_floor = partial(self.make_tile, glyph="x", color=display.WHITE)
        self.entities = [make_floor(i // self.board_size, i % self.board_size) for i in range(self.board_size)]

    def get_tile(self, x, y) -> int:
        return self.entities[(x* display.BOARD_WIDTH)+y]
        # TODO: 50% chance coords backwards
        # how to check?

    def flip_tile(self, console, x, y):
        console.rgb[x, y] = (ord("X"), display.WHITE, display.BLACK)

