# TODO: do we store info about the board size here, or still display?

import random
from dataclasses import dataclass

import esper
import tcod

import components as cmp
import create
import display
import ecs
import typ


def player_position():
    # TODO: fine to crash if player missing?
    pos = ecs.Query(cmp.Player, cmp.Position).cmp(cmp.Position)
    return pos


def coords_within_radius(pos: cmp.Position, radius: int):
    min_x = max(0, pos.x - radius)
    max_x = min(display.BOARD_WIDTH, pos.x + radius + 1)
    min_y = max(0, pos.y - radius)
    max_y = min(display.BOARD_HEIGHT, pos.y + radius + 1)

    ret_coords = []

    for x in range(min_x, max_x):
        for y in range(min_y, max_y):
            current = cmp.Position(x=x, y=y)
            dist = euclidean_distance(pos, current)
            if dist <= radius:
                ret_coords.append([x, y])
    return ret_coords


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
            col = [create.wall(x, y) for y in range(display.BOARD_HEIGHT)]
            self.cells.append(col)

    @classmethod
    def as_rgb(cls, cell: typ.CELL) -> typ.CELL_RGB:
        vis = esper.component_for_entity(cell, cmp.Visible)
        return (vis.glyph, vis.color, vis.bg_color)

    def as_transparency(self) -> list[list[int]]:
        transparency = []
        for _ in range(display.BOARD_WIDTH):
            col = [None for _ in range(display.BOARD_HEIGHT)]
            transparency.append(col)

        for x, col in enumerate(self.cells):
            for y, cell in enumerate(col):
                transparency[x][y] = int(esper.has_component(cell, cmp.Transparent))
        return transparency

    def as_move_graph(self) -> list[list[int]]:
        graph = []
        for _ in range(display.BOARD_WIDTH):
            col = [None for _ in range(display.BOARD_HEIGHT)]
            graph.append(col)

        for x, col in enumerate(self.cells):
            for y, cell in enumerate(col):
                graph[x][y] = int(not (esper.has_component(cell, cmp.Blocking)))
        return graph

    def has_blocker(self, x, y):
        for ent in self.entities[x][y]:
            if esper.has_component(ent, cmp.Player):
                return False
            if esper.has_component(ent, cmp.Blocking):
                return True
        cell = self.cells[x][y]
        return esper.has_component(cell, cmp.Blocking)

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

    def set_cell(self, x: int, y: int, cell: typ.CELL):
        if not self._in_bounds(x, y):
            raise IndexError()
        esper.delete_entity(self.cells[x][y], immediate=True)
        self.cells[x][y] = cell

    def entities_at(self, pos: cmp.Position) -> set:
        return self.entities[pos.x][pos.y]

    def remove(self, entity: int):
        if pos := esper.component_for_entity(entity, cmp.Position):
            esper.remove_component(entity, cmp.Position)
            self.entities_at(pos).remove(entity)

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
            self.entities_at(pos).add(entity)

    def reposition(self, entity: int, x: int, y: int):
        pos = esper.component_for_entity(entity, cmp.Position)
        if entity in self.entities_at(pos):
            self.entities_at(pos).remove(entity)
        pos.x, pos.y = x, y
        self.entities_at(pos).add(entity)


BOARD: Board


@dataclass
class RectangularRoom:
    # TODO: x1 and x2 should both either be inner or outer
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
    def center(self) -> cmp.Position:
        center_x = (self.x1 + self.x2) // 2
        center_y = (self.y1 + self.y2) // 2

        return cmp.Position(x=center_x, y=center_y)

    def get_random_pos(self) -> cmp.Position:
        x = random.randint(self.x1 + 1, self.x2 - 1)
        y = random.randint(self.y1 + 1, self.y2 - 1)
        return cmp.Position(x=x, y=y)

    @property
    def inner(self) -> tuple[slice, slice]:
        """Return the inner area of this room as a 2D array index."""
        return slice(self.x1 + 1, self.x2), slice(self.y1 + 1, self.y2)

    @property
    def outer(self) -> tuple[slice, slice]:
        """Return the inner area of this room as a 2D array index."""
        return slice(self.x1, self.x2 + 1), slice(self.y1, self.y2 + 1)


def tunnel_between(board, start: cmp.Position, end: cmp.Position):
    """Return an L-shaped tunnel between these two points."""
    horizontal_then_vertical = random.random() < 0.5
    if horizontal_then_vertical:
        corner_x, corner_y = end.x, start.y
    else:
        corner_x, corner_y = start.x, end.y

    # Generate the coordinates for this tunnel.
    for x, y in tcod.los.bresenham((start.x, start.y), (corner_x, corner_y)).tolist():
        board.set_cell(x, y, create.floor(x, y))
    for x, y in tcod.los.bresenham((corner_x, corner_y), (end.x, end.y)).tolist():
        board.set_cell(x, y, create.floor(x, y))


def intersects(board: Board, src: RectangularRoom, target: RectangularRoom) -> bool:
    # Checking corner overlap is cheaper, but that doesn't work for non-rect rooms
    src_cells = board.as_sequence(*src.outer)
    target_cells = board.as_sequence(*target.outer)
    return bool(set(src_cells) & (set(target_cells)))


def euclidean_distance(start: cmp.Position, end: cmp.Position):
    return pow(pow(end.x - start.x, 2) + pow(end.y - start.y, 2), 0.5)


def closest_position(start: cmp.Position, options: list[cmp.Position]) -> cmp.Position:
    closest_dist = float("inf")
    closest_coord = None

    for position in options:
        distance = euclidean_distance(start, position)
        if distance < closest_dist:
            closest_dist = distance
            closest_coord = position

    return closest_coord or start


def generate_dungeon(board, max_rooms=30, max_rm_siz=10, min_rm_siz=6):
    rooms: list[RectangularRoom] = []
    centers: list[cmp.Position] = []
    for _ in range(max_rooms):
        room_width = random.randint(min_rm_siz, max_rm_siz)
        room_height = random.randint(min_rm_siz, max_rm_siz)

        room_x = random.randint(0, display.BOARD_WIDTH - room_width - 1)
        room_y = random.randint(0, display.BOARD_HEIGHT - room_height - 1)

        new_room = RectangularRoom(room_x, room_y, room_width, room_height)
        if any(intersects(board, new_room, room) for room in rooms):
            continue  # This room intersects, so go to the next attempt.

        centers.append(new_room.center)
        for cell in board.as_sequence(*new_room.inner):
            pos = esper.component_for_entity(cell, cmp.Position)
            board.set_cell(*pos, create.floor(*pos))

        if len(rooms) == 0:  # start player in first room
            pos = player_position()
            pos.x, pos.y = new_room.center.x, new_room.center.y
        else:  # All rooms after the first get one tunnel and enemy
            endpt = closest_position(new_room.center, centers[:-1])
            tunnel_between(board, new_room.center, endpt)
            for _ in range(random.randint(1, 3)):
                npcs = [create.bat, create.skeleton, create.warlock]
                npc_gen = random.choice(npcs)
                npc_gen(new_room.get_random_pos())

            item = random.choice([create.trap, create.potion, create.scroll])
            item(new_room.get_random_pos())

        rooms.append(new_room)

    last_center = rooms[-1].center
    board.set_cell(*last_center.as_tuple, create.stairs(last_center))
    board.build_entity_cache()


def new_level():
    global BOARD
    old_level = ecs.Query(cmp.Position).exclude(cmp.Player, cmp.Crosshair)
    for to_del, _ in old_level:
        esper.delete_entity(to_del, immediate=True)

    BOARD = Board()
    generate_dungeon(BOARD)


def trace_ray(source: int, dest: int):
    """trace a line between source and dest, returning first blocker and path"""
    global BOARD
    source_pos = esper.component_for_entity(source, cmp.Position)
    dest_pos = esper.component_for_entity(dest, cmp.Position)

    trace = list(tcod.los.bresenham(source_pos.as_tuple, dest_pos.as_tuple))
    for i, (x, y) in enumerate(trace):
        entities = BOARD.entities[x][y]
        for entity in entities:
            if esper.has_component(entity, cmp.Blocking) and entity not in (
                source,
                dest,
            ):
                return entity, trace[: i + 1]

    return dest, trace


def flash_line(line: list):
    for x, y in line:
        pos = cmp.Position(x=x, y=y)
        esper.dispatch_event("flash_pos", pos, display.Color.BLUE)
