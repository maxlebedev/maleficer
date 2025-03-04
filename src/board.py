# do we store info about the board size here, or still display?

import random
from dataclasses import dataclass

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
    def center(self) -> POSITION:
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


def tunnel_between(board, start: POSITION, end: POSITION):
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
        cell = board.get_cell(x, y)
        board.to_floor(cell)
    for x, y in tcod.los.bresenham((corner_x, corner_y), (x2, y2)).tolist():
        cell = board.get_cell(x, y)
        board.to_floor(cell)

def intersects(board: Board, src: RectangularRoom, target: RectangularRoom) -> bool:
    # Checking corner overlap is cheaper, but that doesn't work for non-rect rooms
    src_cells = board.yield_range(*src.outer)
    target_cells = board.yield_range(*target.outer)
    return bool(set(src_cells) & (set(target_cells)))


def closest_coordinate(origin: POSITION, coordinates: list[POSITION]) -> POSITION:
    # Function to calculate the Euclidean distance
    def euclidean_distance(x1, y1, x2, y2):
        return pow(pow(x2-x1,2)+pow(y2-y1,2), 0.5)

    # Initialize the closest distance as a large number
    closest_dist = float('inf')
    closest_coord = None

    # Iterate through the list of coordinates and find the closest one
    for (x2, y2) in coordinates:
        distance = euclidean_distance(origin[0], origin[1], x2, y2)
        if distance < closest_dist:
            closest_dist = distance
            closest_coord = (x2, y2)

    return closest_coord or origin


def generate_dungeon(board, max_rooms=30, max_rm_siz=10, min_rm_siz=6):
    rooms: list[RectangularRoom] = []
    centers: list[POSITION] = []
    for _ in range(max_rooms):
        room_width = random.randint(min_rm_siz, max_rm_siz)
        room_height = random.randint(min_rm_siz, max_rm_siz)

        x = random.randint(0, display.BOARD_WIDTH - room_width - 1)
        y = random.randint(0, display.BOARD_HEIGHT - room_height - 1)

        new_room = RectangularRoom(x, y, room_width, room_height)
        # Run through the other rooms and see if they intersect with this one.
        if any(intersects(board, new_room, other_room) for other_room in rooms):
            continue  # This room intersects, so go to the next attempt.

        centers.append(new_room.center)
        for cell in board.yield_range(*new_room.inner):
            board.to_floor(cell)

        if len(rooms) == 0: # The first room, where the player starts.
            _, (_, pos) = esper.get_components(cmp.Player, cmp.Position)[0]
            pos.x, pos.y = new_room.center
        else:  # All rooms after the first.
            # Dig out a tunnel between this room and the previous one.
            endpt = closest_coordinate(new_room.center, centers[:-1])
            tunnel_between(board, new_room.center, endpt)

        # Finally, append the new room to the list.
        rooms.append(new_room)
