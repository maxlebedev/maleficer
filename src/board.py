# do we store info about the board size here, or still display?

import esper

import components as cmp
import display


class Board:
    """
    Note: the cell matrix is stored as columns, so [x][y] is the right acces pattern
    component access
    pos = esper.component_for_entity(cell, cmp.Position)
    """

    def make_floor(self, x: int, y: int) -> int:
        vis = cmp.Visible(glyph=".", color=display.WHITE)
        cell = esper.create_entity(cmp.Cell(), cmp.Position(x, y), vis)
        return cell

    def make_wall(self, x: int, y: int) -> int:
        vis = cmp.Visible(glyph="X", color=display.WHITE)
        cell = esper.create_entity(cmp.Cell(), cmp.Position(x, y), vis, cmp.Blocking())
        return cell

    def __init__(self):
        self.cells = []
        self.board_size = display.BOARD_WIDTH * display.BOARD_HEIGHT
        for x in range(display.BOARD_WIDTH):
            row = [self.make_floor(x, y) for y in range(display.BOARD_HEIGHT)]
            self.cells.append(row)

    @classmethod
    def cell_to_rgb(cls, cell: int):
        vis = esper.component_for_entity(cell, cmp.Visible)
        return (ord(vis.glyph), vis.color, display.BLACK)

    def get_cell(self, x: int, y: int) -> int:
        return self.cells[x][y]

    def set_cell(
        self, x: int, y: int, glyph: str | None = None, color: display.RGB | None = None
    ):
        vis = esper.component_for_entity(self.cells[x][y], cmp.Visible)
        if glyph:
            vis.glyph = glyph
        if color:
            vis.color = color
