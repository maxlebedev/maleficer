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
    floor_glyph = "."
    wall_glyph = "X"

    def make_floor(self, x: int, y: int) -> int:
        vis = cmp.Visible(glyph=self.floor_glyph, color=display.WHITE)
        cell = esper.create_entity(cmp.Cell(), cmp.Position(x, y), vis)
        return cell

    def make_wall(self, x: int, y: int) -> int:
        vis = cmp.Visible(glyph=self.wall_glyph, color=display.WHITE)
        cell = esper.create_entity(cmp.Cell(), cmp.Position(x, y), vis, cmp.Blocking())
        return cell

    def to_wall(self, cell: int):
        self.set_cell(cell, glyph=self.wall_glyph)
        esper.add_component(cell, cmp.Blocking)

    def to_floor(self, cell: int):
        self.set_cell(cell, glyph=self.floor_glyph)
        esper.remove_component(cell, cmp.Blocking)

    def __init__(self):
        self.cells = []
        self.board_size = display.BOARD_WIDTH * display.BOARD_HEIGHT
        for x in range(display.BOARD_WIDTH):
            row = [self.make_wall(x, y) for y in range(display.BOARD_HEIGHT)]
            self.cells.append(row)

    @classmethod
    def cell_to_rgb(cls, cell: int):
        vis = esper.component_for_entity(cell, cmp.Visible)
        return (ord(vis.glyph), vis.color, display.BLACK)

    def get_cell(self, x: int, y: int) -> int | None:
        # bounds checking
        if any([x < 0, y < 0, x > display.BOARD_WIDTH-1, y > display.BOARD_HEIGHT-1]):
            return None
        return self.cells[x][y]

    def set_cell(self, cell: int, glyph: str | None = None, color: display.RGB | None = None):
        vis = esper.component_for_entity(cell, cmp.Visible)
        if glyph:
            vis.glyph = glyph
        if color:
            vis.color = color

    def yield_range(self, x_slice: slice, y_slice: slice):
        for col in self.cells[x_slice]:
            for cell in col[y_slice]:
                yield cell


class RectangularRoom:
    def __init__(self, x: int, y: int, width: int, height: int):
        self.x1 = x
        self.y1 = y
        self.x2 = x + width
        self.y2 = y + height

    @property
    def inner(self) -> tuple[slice, slice]:
        """Return the inner area of this room as a 2D array index."""
        return slice(self.x1 + 1, self.x2), slice(self.y1 + 1, self.y2)


def generate_dungeon(board):

    room1 = RectangularRoom(x=20, y=15, width=10, height=15)
    room2 = RectangularRoom(x=35, y=15, width=10, height=15)
    room3 = RectangularRoom(x=0, y=0, width=15, height=10)
    rooms = [room1, room2, room3]
    for room in rooms:
        for cell in board.yield_range(*room.inner):
            board.to_floor(cell)
