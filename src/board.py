# do we store info about the board size here, or still display?

import random
from collections.abc import Generator

import esper
import tcod

import components as cmp
import display

POSITION = tuple[int, int]


class Board:
    """
    Note: the cell matrix is stored as columns, so [x][y] is the right acces pattern
    component access
    pos = esper.component_for_entity(cell, cmp.Position)
    """

    floor_glyph = "."
    wall_glyph = "#"

    def make_floor(self, x: int, y: int) -> int:
        vis = cmp.Visible(glyph=self.floor_glyph, color=display.WHITE)
        cell = esper.create_entity(cmp.Cell(), cmp.Position(x, y), vis)
        return cell

    def make_wall(self, x: int, y: int) -> int:
        vis = cmp.Visible(glyph=self.wall_glyph, color=display.WHITE)
        cell = esper.create_entity(cmp.Cell(), cmp.Position(x, y), vis, cmp.Blocking())
        return cell

    def to_wall(self, cell: int):
        self.set_glyph(cell, glyph=self.wall_glyph)
        esper.add_component(cell, cmp.Blocking)

    def to_floor(self, cell: int):
        self.set_glyph(cell, glyph=self.floor_glyph)
        if esper.has_component(cell, cmp.Blocking):
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
        if any(
            [x < 0, y < 0, x > display.BOARD_WIDTH - 1, y > display.BOARD_HEIGHT - 1]
        ):
            return None
        return self.cells[x][y]

    def set_glyph(self, cell: int, glyph: str):
        vis = esper.component_for_entity(cell, cmp.Visible)
        vis.glyph = glyph

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


def tunnel_between(start: POSITION, end: POSITION) -> Generator[POSITION, None, None]:
    """Return an L-shaped tunnel between these two points."""
    x1, y1 = start
    x2, y2 = end
    if random.random() < 0.5:
        # Move horizontally, then vertically.
        corner_x, corner_y = x2, y1
    else:
        # Move vertically, then horizontally.
        corner_x, corner_y = x1, y2

    # Generate the coordinates for this tunnel.
    for x, y in tcod.los.bresenham((x1, y1), (corner_x, corner_y)).tolist():
        yield x, y
    for x, y in tcod.los.bresenham((corner_x, corner_y), (x2, y2)).tolist():
        yield x, y

def interects(board: Board, src: RectangularRoom, target: RectangularRoom) -> bool:
    src_cells = board.yield_range(*src.inner)
    target_cells = board.yield_range(*target.inner)
    return set(src_cells) == set(target_cells)


def generate_dungeon(board):
    room1 = RectangularRoom(x=20, y=15, width=10, height=15)
    room2 = RectangularRoom(x=35, y=15, width=10, height=15)
    room3 = RectangularRoom(x=0, y=0, width=15, height=10)
    rooms = [room1, room2, room3]
    for room in rooms:
        for cell in board.yield_range(*room.inner):
            board.to_floor(cell)

    tunnel1 = tunnel_between((30, 20), (40, 20))
    tunnel2 = tunnel_between((5, 5), (40, 23))
    for tunnel in [tunnel1, tunnel2]:
        for x, y in tunnel:
            cell = board.get_cell(x, y)
            board.to_floor(cell)
