# do we store info about the board size here?
from functools import partial

import esper

import components as cmp
import display


class Board:
    """
        Note: the tiles matrix is stored as columns, so [x][y] is the right acces pattern
        component access
        pos = esper.component_for_entity(tile, cmp.Position)
    """
    def make_tile(self, x, y, glyph, color):
        visible_cmp = cmp.Visible(glyph=glyph, color=color)
        tile = esper.create_entity(cmp.Tile(), cmp.Position(x,y), visible_cmp )
        # walls are #visible #blocking
        return tile

    def __init__(self):
        self.tiles = []
        self.board_size = display.BOARD_WIDTH*display.BOARD_HEIGHT
        for x in range(display.BOARD_WIDTH):
            mt = partial(self.make_tile, glyph=".", color=display.WHITE)
            row = [mt(x, y) for y in range(display.BOARD_HEIGHT)]

            self.tiles.append(row)

    @classmethod
    def tile_to_rgb(cls, tile):
        vis = esper.component_for_entity(tile, cmp.Visible)
        return (ord(vis.glyph), vis.color, display.BLACK)

    def get_tile(self, x, y) -> int:
        return self.tiles[x][y]

    def set_tile(self, x, y, glyph = None, color = None):
        vis = esper.component_for_entity(self.tiles[x][y], cmp.Visible)
        if glyph:
            vis.glyph = glyph
        if color:
            vis.color = color

