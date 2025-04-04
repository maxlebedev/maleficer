# TODO: do we store info about the board size here, or still display?

import random
from dataclasses import dataclass

import esper
import tcod

import components as cmp
import display
import typ


def player_position():
    # TODO: fine to crash if player missing?
    _, (_, pos) = esper.get_components(cmp.Player, cmp.Position)[0]
    return pos


class Board:
    """
    Note: the cell matrix is stored as columns, so [x][y] is the right acces pattern
    """

    cells: list[list[typ.CELL]] = []
    entities: list[list[set[int]]] = []
    explored: set[typ.CELL] = set()

    def __init__(self):
        self.entities = [
            [set() for _ in range(display.BOARD_HEIGHT)]
            for _ in range(display.BOARD_WIDTH)
        ]
        self.cells = []
        self.board_size = display.BOARD_WIDTH * display.BOARD_HEIGHT
        for x in range(display.BOARD_WIDTH):
            col = [self.make_wall(x, y) for y in range(display.BOARD_HEIGHT)]
            self.cells.append(col)

    def make_floor(self, x: int, y: int) -> int:
        vis = cmp.Visible(glyph=display.Glyph.FLOOR, color=display.Color.LGREY)
        cell = esper.create_entity(
            cmp.Cell(), cmp.Position(x, y), vis, cmp.Transparent()
        )
        return cell

    def make_wall(self, x: int, y: int) -> int:
        vis = cmp.Visible(glyph=display.Glyph.WALL, color=display.Color.LGREY)
        cell = esper.create_entity(cmp.Cell(), cmp.Position(x, y), vis, cmp.Blocking())
        return cell

    def make_bat(self, x: int, y: int) -> int:
        pos = cmp.Position(x, y)
        vis = cmp.Visible(glyph=display.Glyph.BAT, color=display.Color.RED)
        actor = cmp.Actor(max_hp=1, name="bat")
        components = [cmp.Enemy(), pos, vis, cmp.Blocking(), cmp.Enemy(), actor]
        bat = esper.create_entity(*components)
        return bat

    @classmethod
    def as_rgb(cls, cell: typ.CELL) -> typ.CELL_RGB:
        vis = esper.component_for_entity(cell, cmp.Visible)
        return (vis.glyph, vis.color, vis.bg_color)

    def as_transparency(self) -> list[list[bool]]:
        transparency = []
        for _ in range(display.BOARD_WIDTH):
            col = [None for _ in range(display.BOARD_HEIGHT)]
            transparency.append(col)

        for x, col in enumerate(self.cells):
            for y, cell in enumerate(col):
                transparency[x][y] = int(esper.has_component(cell, cmp.Transparent))
        return transparency

    def _in_bounds(self, x: int, y: int) -> bool:
        if x < 0 or y < 0:
            return False
        if x > display.BOARD_WIDTH - 1 or y > display.BOARD_HEIGHT - 1:
            return False
        return True

    def get_cell(self, x: int, y: int) -> typ.CELL | None:
        if self._in_bounds(x, y):
            return self.cells[x][y]
        return None

    def remove_cell(self, x: int, y: int):
        esper.delete_entity(self.cells[x][y])

    def set_cell(self, x: int, y: int, cell: typ.CELL):
        if not self._in_bounds(x, y):
            raise IndexError()
        self.remove_cell(x, y)
        self.cells[x][y] = cell

    def set_glyph(self, cell: typ.CELL, glyph: int):
        vis = esper.component_for_entity(cell, cmp.Visible)
        vis.glyph = glyph

    def as_sequence(self, x_slice: slice = slice(None), y_slice: slice = slice(None)):
        for col in self.cells[x_slice]:
            for cell in col[y_slice]:
                yield cell

    def build_entity_cache(self):
        for x in range(display.BOARD_WIDTH):
            for y in range(display.BOARD_HEIGHT):
                self.entities[x][y] = set()
        for entity, pos in esper.get_component(cmp.Position):
            self.entities[pos.x][pos.y].add(entity)


@dataclass
class RectangularRoom:
    x1: int
    y1: int
    width: int
    height: int

    @property
    def x2(self):
        return self.x1 + self.width

    @property
    def y2(self):
        return self.y1 + self.height

    @property
    def center(self) -> typ.POSITION:
        center_x = (self.x1 + self.x2) // 2
        center_y = (self.y1 + self.y2) // 2

        return center_x, center_y

    @property
    def inner(self) -> tuple[slice, slice]:
        """Return the inner area of this room as a 2D array index."""
        return slice(self.x1 + 1, self.x2), slice(self.y1 + 1, self.y2)

    @property
    def outer(self) -> tuple[slice, slice]:
        """Return the inner area of this room as a 2D array index."""
        return slice(self.x1, self.x2 + 1), slice(self.y1, self.y2 + 1)


def tunnel_between(board, start: typ.POSITION, end: typ.POSITION):
    """Return an L-shaped tunnel between these two points."""
    x1, y1 = start
    x2, y2 = end
    horizontal_then_vertical = random.random() < 0.5
    if horizontal_then_vertical:
        corner_x, corner_y = x2, y1
    else:
        corner_x, corner_y = x1, y2

    # Generate the coordinates for this tunnel.
    for x, y in tcod.los.bresenham((x1, y1), (corner_x, corner_y)).tolist():
        board.set_cell(x, y, board.make_floor(x, y))
    for x, y in tcod.los.bresenham((corner_x, corner_y), (x2, y2)).tolist():
        board.set_cell(x, y, board.make_floor(x, y))


def intersects(board: Board, src: RectangularRoom, target: RectangularRoom) -> bool:
    # Checking corner overlap is cheaper, but that doesn't work for non-rect rooms
    src_cells = board.as_sequence(*src.outer)
    target_cells = board.as_sequence(*target.outer)
    return bool(set(src_cells) & (set(target_cells)))


def closest_position(start: typ.POSITION, position: list[typ.POSITION]) -> typ.POSITION:
    def euclidean_distance(x1, y1, x2, y2):
        return pow(pow(x2 - x1, 2) + pow(y2 - y1, 2), 0.5)

    # Initialize the closest distance as a large number
    closest_dist = float("inf")
    closest_coord = None

    # Iterate through the list of coordinates and find the closest one
    for x2, y2 in position:
        distance = euclidean_distance(start[0], start[1], x2, y2)
        if distance < closest_dist:
            closest_dist = distance
            closest_coord = (x2, y2)

    return closest_coord or start


def generate_dungeon(board, max_rooms=30, max_rm_siz=10, min_rm_siz=6):
    rooms: list[RectangularRoom] = []
    centers: list[typ.POSITION] = []
    for _ in range(max_rooms):
        room_width = random.randint(min_rm_siz, max_rm_siz)
        room_height = random.randint(min_rm_siz, max_rm_siz)

        x = random.randint(0, display.BOARD_WIDTH - room_width - 1)
        y = random.randint(0, display.BOARD_HEIGHT - room_height - 1)

        new_room = RectangularRoom(x, y, room_width, room_height)
        if any(intersects(board, new_room, other_room) for other_room in rooms):
            continue  # This room intersects, so go to the next attempt.

        centers.append(new_room.center)
        for cell in board.as_sequence(*new_room.inner):
            pos = esper.component_for_entity(cell, cmp.Position)
            board.set_cell(pos.x, pos.y, board.make_floor(pos.x, pos.y))

        if len(rooms) == 0:  # start player in first room
            pos = player_position()
            pos.x, pos.y = new_room.center
        else:  # All rooms after the first get one tunnel and bat
            endpt = closest_position(new_room.center, centers[:-1])
            tunnel_between(board, new_room.center, endpt)
            board.make_bat(*new_room.center)

        rooms.append(new_room)
