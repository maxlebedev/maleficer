# TODO: do we store info about the board size here, or still display?

import random
from dataclasses import dataclass
from typing import Callable

import esper
import tcod

import components as cmp
import create
import display
import ecs
import math_util
import typ


def player_position():
    pos = ecs.Query(cmp.Player).cmp(cmp.Position)
    return pos


def player_last_position():
    lp = ecs.Query(cmp.Player).cmp(cmp.LastPosition)
    return lp.pos

def get_board():
    game_meta = ecs.Query(cmp.GameMeta).val
    return game_meta.board


def can_see(entity: int, target: int, distance: int | None = None) -> bool:
    dest_cell, trace = trace_ray(entity, target)
    if dest_cell != target:  # no LOS
        return False
    if distance and len(trace) > distance:
        return False
    return True


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

    def fill(self):
        def make_wall(x, y):
            if x in (0, display.BOARD_WIDTH - 1):
                return create.tile.wall(x, y)
            if y in (0, display.BOARD_HEIGHT - 1):
                return create.tile.wall(x, y)
            return create.tile.wall(x, y, breakable=not random.randint(0, 15))

        for x in range(display.BOARD_WIDTH):
            col = [make_wall(x, y) for y in range(display.BOARD_HEIGHT)]
            self.cells.append(col)

    @classmethod
    def as_rgb(cls, cell: typ.CELL) -> typ.CELL_RGB:
        vis = esper.component_for_entity(cell, cmp.Visible)
        return (vis.glyph, vis.color, vis.bg_color)

    def as_transparency(self) -> list[typ.COORD]:
        transparency = []
        for _ in range(display.BOARD_WIDTH):
            col = [None for _ in range(display.BOARD_HEIGHT)]
            transparency.append(col)

        for x, col in enumerate(self.cells):
            for y, cell in enumerate(col):
                transparency[x][y] = int(esper.has_component(cell, cmp.Transparent))
        return transparency

    def as_move_graph(self) -> list[typ.COORD]:
        graph = []
        for _ in range(display.BOARD_WIDTH):
            col = [None for _ in range(display.BOARD_HEIGHT)]
            graph.append(col)

        for x, col in enumerate(self.cells):
            for y, _ in enumerate(col):
                graph[x][y] = int(not (self.has_blocker(x, y)))
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

    def get_cell(self, x: int, y: int) -> typ.CELL:
        if self._in_bounds(x, y):
            return self.cells[x][y]
        raise Exception(f"No such cell {x=} {y=}")

    def set_cell(self, x: int, y: int, cell: typ.CELL):
        if not self._in_bounds(x, y):
            raise IndexError()
        esper.delete_entity(self.cells[x][y], immediate=True)
        self.cells[x][y] = cell

    def retile(self, x: int, y: int, gen_tile: Callable):
        """create a tile and place it at position"""
        self.set_cell(x, y, gen_tile(x, y))

    def entities_at(self, pos: cmp.Position) -> set:
        return self.entities[pos.x][pos.y]

    def pieces_at(self, pos: cmp.Position) -> set:
        """entities, but without cells, crosshair, etc"""
        entities = self.entities[pos.x][pos.y]
        cell = self.cells[pos.x][pos.y]
        xhair = ecs.Query(cmp.Crosshair).first()
        return {e for e in entities if e not in [cell, xhair]}

    def remove(self, entity: int):
        if pos := esper.component_for_entity(entity, cmp.Position):
            esper.remove_component(entity, cmp.Position)
            self.entities_at(pos).remove(entity)

    def set_glyph(self, cell: typ.CELL, glyph: int):
        vis = esper.component_for_entity(cell, cmp.Visible)
        vis.glyph = glyph

    def as_sequence(self, x: slice = slice(None), y: slice = slice(None)):
        for col in self.cells[x]:
            for cell in col[y]:
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
            self.entities[pos.x][pos.y].remove(entity)
        pos.x, pos.y = x, y
        self.entities[x][y].add(entity)


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
        board.retile(x, y, create.tile.floor)
    for x, y in tcod.los.bresenham((corner_x, corner_y), (end.x, end.y)).tolist():
        board.retile(x, y, create.tile.floor)


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
    board.fill()
    rooms: list[RectangularRoom] = []
    centers: list[cmp.Position] = []
    for _ in range(max_rooms):
        room_width = random.randint(min_rm_siz, max_rm_siz)
        room_height = random.randint(min_rm_siz, max_rm_siz)

        room_x = random.randint(0, display.BOARD_WIDTH - room_width - 1)
        room_y = random.randint(0, display.BOARD_HEIGHT - room_height - 1)

        new_room = RectangularRoom(room_x, room_y, room_width, room_height)
        if any(intersects(board, new_room, room) for room in rooms):
            continue  # This room intersects, so go to the next attempt

        centers.append(new_room.center)
        for cell in board.as_sequence(*new_room.inner):
            pos = esper.component_for_entity(cell, cmp.Position)
            board.retile(*pos, create.tile.floor)

        if len(rooms) == 0:  # start player in first room
            pos = player_position()
            pos.x, pos.y = new_room.center.x, new_room.center.y
        else:  # All rooms after the first get one tunnel and enemy
            endpt = closest_position(new_room.center, centers[:-1])
            tunnel_between(board, new_room.center, endpt)
            for _ in range(random.randint(1, 3)):
                npcs = [
                    create.npc.bat,
                    create.npc.skeleton,
                    create.npc.warlock,
                ]
                weights = [3, 2, 1]
                npc_gen = random.choices(npcs, weights)[0]
                npc_gen(new_room.get_random_pos())

            item = random.choice(
                [create.item.trap, create.item.potion, create.item.scroll]
            )
            item(new_room.get_random_pos())

        rooms.append(new_room)

    last_center = rooms[-1].center
    board.retile(*last_center, create.tile.stairs)


def new_level():
    old_level = ecs.Query(cmp.Position).exclude(cmp.Player, cmp.Crosshair)
    for to_del, _ in old_level:
        esper.delete_entity(to_del, immediate=True)

    game_meta = ecs.Query(cmp.GameMeta).val
    game_meta.mood = display.Mood.shuffle()
    game_meta.board = Board()
    levels = [generate_dungeon, cave_dungeon, maze_dungeon]
    level_func = random.choice(levels)
    level_func(game_meta.board)
    game_meta.board.build_entity_cache()


def trace_ray(source: int, dest: int):
    """trace a line between source  dest,
    return first blocker & inclusive path"""
    board = get_board()
    source_pos = esper.component_for_entity(source, cmp.Position)
    dest_pos = esper.component_for_entity(dest, cmp.Position)

    trace = list(tcod.los.bresenham(source_pos.as_tuple, dest_pos.as_tuple))
    for i, (x, y) in enumerate(trace):
        entities = board.entities[x][y]
        for entity in entities:
            if esper.has_component(entity, cmp.Blocking):
                if entity not in (source, dest):
                    return entity, trace[: i + 1]

    return dest, trace


def get_fov():
    board = get_board()
    transparency = board.as_transparency()
    pos = player_position()
    algo = tcod.libtcodpy.FOV_SHADOW
    fov = tcod.map.compute_fov(transparency, pos.as_tuple, radius=4, algorithm=algo)
    return fov


def get_neighbor_coords(pos: cmp.Position):
    offsets = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    indices = [(pos.x + dx, pos.y + dy) for dx, dy in offsets]
    return indices


def count_neighbors(board, pos: cmp.Position):
    indices = get_neighbor_coords(pos)
    neighbor_walls = 0
    for x, y in indices:
        try:
            cell = board.get_cell(x, y)
            if esper.has_component(cell, cmp.Wall):
                neighbor_walls += 1
        except Exception:
            pass
    return neighbor_walls


def build_perimeter_wall(board):
    border = {(0, y) for y in range(display.BOARD_HEIGHT)}
    border |= {(display.BOARD_WIDTH - 1, y) for y in range(display.BOARD_HEIGHT)}
    border |= {(x, 0) for x in range(display.BOARD_WIDTH)}
    border |= {(x, display.BOARD_HEIGHT - 1) for x in range(display.BOARD_WIDTH)}

    for x, y in border:
        board.retile(x, y, create.tile.wall)


def cave_dungeon(board):
    board.fill()
    for cell in board.as_sequence():
        if not random.randint(0, 1):
            cell_pos = esper.component_for_entity(cell, cmp.Position)
            board.retile(*cell_pos, create.tile.floor)
    # Horizontal Blanking
    x_slice = slice(3, display.BOARD_WIDTH - 3)
    midpoint = display.BOARD_HEIGHT // 2
    y_slice = slice(midpoint - 1, midpoint + 2)
    for cell in board.as_sequence(x_slice, y_slice):
        player_pos = esper.component_for_entity(cell, cmp.Position)
        board.retile(*player_pos, create.tile.floor)

    neighbours = [
        [0 for _ in range(display.BOARD_HEIGHT)] for _ in range(display.BOARD_WIDTH)
    ]
    celL_autamata_passes = 4
    for _ in range(celL_autamata_passes):
        for cell in board.as_sequence():
            player_pos = esper.component_for_entity(cell, cmp.Position)
            wall_count = count_neighbors(board, player_pos)
            neighbours[player_pos.x][player_pos.y] = wall_count
    for x, row in enumerate(neighbours):
        for y in range(len(row)):
            tile = None
            if neighbours[x][y] >= 5:
                breakable = not random.randint(0, 15)
                tile = create.tile.wall(x, y, breakable=breakable)
            elif neighbours[x][y] <= 4:
                tile = create.tile.floor(x, y)
            if tile:
                board.set_cell(x, y, tile)
    build_perimeter_wall(board)
    #TODO: the 3 cells closes to corner should be wall too

    player_pos = player_position()
    player_pos.x = display.BOARD_WIDTH // 2
    player_pos.y = display.BOARD_HEIGHT // 2

    valid_spawns = []
    while len(valid_spawns) < 20:
        x = random.randint(0, display.BOARD_WIDTH - 1)
        y = random.randint(0, display.BOARD_HEIGHT - 1)
        cell = board.cells[x][y]
        pos = esper.component_for_entity(cell, cmp.Position)
        wall_count = count_neighbors(board, pos)
        if wall_count == 0:
            dist = euclidean_distance(player_pos, pos)
            valid_spawns.append([dist, pos])
    valid_spawns = sorted(valid_spawns, key=lambda x: x[0])
    board.retile(*valid_spawns[-1][1], create.tile.stairs)

    spawn_table = {
        create.item.trap: 3,
        create.item.potion: 2,
        create.item.scroll: 1,
        create.npc.bat: 5,
        create.npc.goblin: 3,
        create.npc.warlock: 1,
    }
    for _, pos in valid_spawns[:-1]:
        spawn = math_util.from_table(spawn_table)
        spawn(pos)


def in_player_perception(pos: cmp.Position):
    """true if the source is close enough for player to hear"""
    PLAYER_PERCEPTION_RADIUS = 10
    player_pos = player_position()
    dist_to_player = euclidean_distance(player_pos, pos)
    return dist_to_player < PLAYER_PERCEPTION_RADIUS


def make_maze_blueprint():
    """
    1/4 scale blueprint for maze
    every every odd coord pair is a wall
    we start at a random location and pick a neighbor at random
    add current space to backtrack stack
    break wall between current and neighbor. Add both to visited set
    then pick an unvisited neighbor and repeat
    when there are no neighbors, pop stack and try again for that space
    """
    end_x = display.BOARD_WIDTH // 2
    end_y = display.BOARD_HEIGHT // 2
    blueprint = []
    for _ in range(end_x):
        blueprint.append([1 for _ in range(end_y + 1)])

    # even coord pairs are floor nodes, to be connected
    for x in range(end_x):
        for y in range(end_y):
            if x % 2 == 1 and y % 2 == 1:
                blueprint[x][y] = 0

    start_x = random.choice([15, 17])
    start_y = random.choice([15, 17])

    def get_neighbors(seen: list, c_x: int, c_y: int):
        offsets = [(-2, 0), (0, -2), (0, 2), (2, 0)]
        indices = [(c_x + dx, c_y + dy) for dx, dy in offsets]

        neighbors = []
        for x, y in indices:
            if x > 0 and x < end_x - 1 and y > 0 and y < end_y:
                if [x, y] not in seen:
                    neighbors.append([x, y])
        return neighbors

    def break_wall_between(coord1, coord2):
        x = (coord1[0] + coord2[0]) // 2
        y = (coord1[1] + coord2[1]) // 2

        blueprint[x][y] = 0

    current = [start_x, start_y]
    backtrack = [current]
    seen = [current]
    while backtrack:
        n = get_neighbors(seen, *current)
        if n:
            next = random.choice(n)
            break_wall_between(current, next)
            backtrack.append(next)
            current = next
            seen.append(current)
        else:
            current = backtrack.pop()
    return blueprint, seen


def maze_dungeon(board: Board):
    board.fill()
    blueprint, seen = make_maze_blueprint()
    player_pos = player_position()

    hydrate = lambda x: x * 2

    player_pos.x, player_pos.y = map(hydrate, seen[-1])
    stair_x, stair_y = map(hydrate, seen[0])

    for cell in board.as_sequence():
        pos = esper.component_for_entity(cell, cmp.Position)
        bx = pos.x // 2
        by = pos.y // 2
        if blueprint[bx][by]:
            cell = create.tile.wall(*pos)
        else:
            cell = create.tile.floor(*pos)
        board.set_cell(pos.x, pos.y, cell)
    board.retile(stair_x, stair_y, create.tile.stairs)

    spawn_table = {
        create.item.trap: 3,
        create.item.potion: 2,
        create.item.scroll: 1,
        create.npc.bat: 5,
        create.npc.goblin: 3,
        create.npc.warlock: 1,
    }

    for x, y in seen[1:-1]:
        if not random.randint(0, 2):
            continue

        offset = random.choice([(0, 0), (1, 0), (0, 1), (1, 1)])
        spawn_x = 2 * x + offset[0]
        spawn_y = 2 * y + offset[1]
        pos = cmp.Position(x=spawn_x, y=spawn_y)

        spawn = math_util.from_table(spawn_table)
        spawn(pos)


def generate_test_dungeon(board):
    """one room, one enemy, one item"""
    board.fill()
    room_x = display.BOARD_WIDTH // 2
    room_y = display.BOARD_HEIGHT // 2
    new_room = RectangularRoom(room_x, room_y, 10, 10)
    for cell in board.as_sequence(*new_room.inner):
        pos = esper.component_for_entity(cell, cmp.Position)
        board.retile(*pos, create.tile.floor)

    pos = player_position()
    pos.x, pos.y = new_room.center.x, new_room.center.y
    create.npc.cyclops(new_room.get_random_pos())
    create.item.potion(new_room.get_random_pos())
    create.item.scroll(new_room.get_random_pos())
    board.build_entity_cache()
