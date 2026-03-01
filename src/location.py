# TODO: do we store info about the board size here, or still display?

import random
from dataclasses import dataclass
from typing import Callable, Iterable

import esper
import tcod
import math

import components as cmp
import create
import display
import ecs
import math_util
import typ

BOARD_MAX = display.BOARD_WIDTH - 1


def player_position() -> cmp.Position:
    pos = ecs.Query(cmp.Player).cmp(cmp.Position)
    return pos


def player_last_position() -> cmp.Position:
    lp = ecs.Query(cmp.Player).cmp(cmp.LastPosition)
    return lp.pos


def get_board():
    game_meta = ecs.Query(cmp.GameMeta).val
    return game_meta.board


def matrix(x: int, y: int, val: int):
    return [[val for _ in range(x)] for _ in range(y)]


def get_coord(source: typ.Entity) -> typ.Coord:
    source_pos = esper.component_for_entity(source, cmp.Position)
    return source_pos.as_list


def can_see(
    source: typ.Entity, target: typ.Entity, distance: int | None = None
) -> bool:
    dest_cell, trace = trace_ray(source, target)
    if dest_cell != target:  # no LOS
        return False
    if distance and len(trace) > distance:
        return False
    return True


def coords_within_radius(pos: cmp.Position, radius: int) -> list[typ.Coord]:
    min_x = max(0, pos.x - radius)
    max_x = min(display.BOARD_WIDTH, pos.x + radius + 1)
    min_y = max(0, pos.y - radius)
    max_y = min(display.BOARD_HEIGHT, pos.y + radius + 1)

    ret_coords = []

    for x in range(min_x, max_x):
        for y in range(min_y, max_y):
            dist = math.dist(pos.as_tuple, (x, y))
            if dist <= radius:
                ret_coords.append([x, y])
    return ret_coords


def coords_line_to_point(source: cmp.Position, dest: cmp.Position) -> list[typ.Coord]:
    """exclude source"""
    coords = tcod.los.bresenham(source.as_tuple, dest.as_tuple)
    return list(coords)[1:]


def backlight(x, y):
    """add a fading candle-colored illumination of the player's sight radius"""
    # we then darken the bg light by its distance from the light src player
    player_pos = player_position()
    dist_to_player = math.dist(player_pos.as_tuple, (x, y))
    player_cmp = ecs.Query(cmp.Player).val

    normalized_dist = dist_to_player / player_cmp.sight_radius
    interpolation_coef = 0.85  # higher is faster dropoff
    factor = 1.0 - (normalized_dist * normalized_dist * interpolation_coef)
    bg = display.darker(display.Color.CANDLE, factor=factor)
    return bg


class Board:
    """
    Note: the cell matrix is stored as columns, so [x][y] is the right acces pattern
    """

    cells: list[list[typ.CELL]] = []
    entities: list[list[set[typ.Entity]]] = []
    explored: set[typ.CELL] = set()

    def __init__(self):
        self.entities = [
            [set() for _ in range(display.BOARD_HEIGHT)]
            for _ in range(display.BOARD_WIDTH)
        ]
        self.cells = []

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

    def as_transparency(self) -> list[typ.Coord]:
        transparency = matrix(display.BOARD_WIDTH, display.BOARD_HEIGHT, 1)

        for x in range(display.BOARD_WIDTH):
            for y in range(display.BOARD_HEIGHT):
                is_opaque = lambda x: esper.has_component(x, cmp.Opaque)
                if any(map(is_opaque, self.entities_at(x, y))):
                    transparency[x][y] = 0

        return transparency

    def as_move_graph(self) -> list[typ.Coord]:
        graph = matrix(display.BOARD_WIDTH, display.BOARD_HEIGHT, 1)

        for x, col in enumerate(self.cells):
            for y, _ in enumerate(col):
                graph[x][y] = int(not (self.has_blocker(x, y)))
        return graph

    def has_blocker(self, x, y):
        for ent in self.entities[x][y]:
            # TODO: Is it safe to remove this player check?
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
        raise IndexError(f"No such cell {x=} {y=}")

    def set_cell(self, x: int, y: int, cell: typ.CELL):
        if not self._in_bounds(x, y):
            raise IndexError()
        esper.delete_entity(self.cells[x][y], immediate=True)
        self.cells[x][y] = cell

    def retile(self, x: int, y: int, gen_tile: Callable):
        """create a tile and place it at position"""
        self.set_cell(x, y, gen_tile(x, y))

    def entities_at(self, x: int, y: int) -> set:
        """a reference to the entity set at an xy"""
        return self.entities[x][y]

    def pieces_at(self, x: int, y: int) -> set:
        """entities, but without cells, crosshair, etc"""
        entities = self.entities[x][y]
        cell = self.cells[x][y]
        xhair = ecs.Query(cmp.Crosshair).first()
        return {e for e in entities if e not in [cell, xhair]}

    def remove(self, entity: int):
        if pos := esper.component_for_entity(entity, cmp.Position):
            esper.remove_component(entity, cmp.Position)
            self.entities_at(*pos).remove(entity)

    def as_sequence(self, x: slice = slice(None), y: slice = slice(None)):
        for col in self.cells[x]:
            for cell in col[y]:
                yield cell

    def build_entity_cache(self):
        for x in range(display.BOARD_WIDTH):
            for y in range(display.BOARD_HEIGHT):
                self.entities[x][y] = set()
        for entity, pos in esper.get_component(cmp.Position):
            self.entities_at(*pos).add(entity)

    def reposition(self, entity: int, x: int, y: int):
        pos = esper.component_for_entity(entity, cmp.Position)
        if entity in self.entities_at(*pos):
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
        """Return the outer area of this room as a 2D array index."""
        return slice(self.x1, self.x2 + 1), slice(self.y1, self.y2 + 1)

    @property
    def border_coords(self) -> list:
        """Return the coords of the edges, without corners."""
        top_edge = [(x, self.y1) for x in range(self.x1 + 1, self.x2)]
        bottom_edge = [(x, self.y2) for x in range(self.x1 + 1, self.x2)]
        left_edge = [(self.x1, y) for y in range(self.y1 + 1, self.y2)]
        right_edge = [(self.x2, y) for y in range(self.y1 + 1, self.y2)]
        border = top_edge + bottom_edge + left_edge + right_edge
        return border


def connect_rooms(first: RectangularRoom, second: RectangularRoom):
    board = get_board()
    pair = get_closest_pair(first.border_coords, second.border_coords)
    tunnel_between(*pair[0], *pair[1])

    if not random.randint(0, 1) and math.dist(*pair) > 3:
        # make doors, half the time I guess
        board.retile(*pair[0], create.tile.door)
        board.retile(*pair[1], create.tile.door)


def tunnel_between(start_x: int, start_y: int, end_x: int, end_y: int):
    """Return an L-shaped tunnel between these two points."""
    horizontal_then_vertical = random.random() < 0.5

    if horizontal_then_vertical:
        corner = end_x, start_y
    else:
        corner = start_x, end_y

    board = get_board()
    # Generate the coordinates for this tunnel.
    for x, y in tcod.los.bresenham((start_x, start_y), corner):
        board.retile(x, y, create.tile.floor)
    for x, y in tcod.los.bresenham(corner, (end_x, end_y)):
        board.retile(x, y, create.tile.floor)


def intersects(board: Board, src: RectangularRoom, target: RectangularRoom) -> bool:
    # Checking corner overlap is cheaper, but that doesn't work for non-rect rooms
    src_cells = board.as_sequence(*src.outer)
    target_cells = board.as_sequence(*target.outer)
    return bool(set(src_cells) & (set(target_cells)))


def euclidean_distance(start: cmp.Position, end: cmp.Position):
    return math.dist(start.as_tuple, end.as_tuple)


def manhattan_distance(start: cmp.Position, end: cmp.Position):
    p1 = start.as_tuple
    p2 = end.as_tuple
    return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])


def get_closest_pair(first: Iterable, second: Iterable) -> tuple:
    # TODO: very DRY with closest_position

    min_dist = math.inf
    closest_pair = None

    for p1 in first:
        for p2 in second:
            dist = math.dist(p1, p2)  # euclidean distance
            if dist < min_dist:
                min_dist = dist
                closest_pair = (p1, p2)
    return closest_pair  # type: ignore


def trace_ray(source: int, dest: int):
    """trace a line between source  dest,
    return first blocker & inclusive path"""
    # TODO: I don't like that this returns two different values,
    # and we should probably take pos as args
    board = get_board()

    source_pos = esper.component_for_entity(source, cmp.Position)
    dest_pos = esper.component_for_entity(dest, cmp.Position)

    trace = list(tcod.los.bresenham(source_pos.as_tuple, dest_pos.as_tuple))
    for i, (x, y) in enumerate(trace):
        entities = board.entities[x][y]
        for entity in entities:
            if esper.has_component(entity, cmp.Opaque):
                if entity not in (source, dest):
                    return entity, trace[: i + 1]

    return dest, trace


def get_fov():
    board = get_board()
    transparency = board.as_transparency()
    pos = player_position()
    player_cmp = ecs.Query(cmp.Player).val
    radius = player_cmp.sight_radius
    algo = tcod.libtcodpy.FOV_SHADOW

    fov = tcod.map.compute_fov(
        transparency, pos.as_tuple, radius=radius, algorithm=algo
    )
    return fov


def get_neighbor_coords(x: int, y: int):
    offsets = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    indices = [(x + dx, y + dy) for dx, dy in offsets]
    return indices


def count_neighbors(board, x: int, y: int):
    indices = get_neighbor_coords(x, y)
    neighbor_walls = 0
    for x, y in indices:
        try:
            cell = board.get_cell(x, y)
            if esper.has_component(cell, cmp.Wall):
                neighbor_walls += 1
        except IndexError:
            pass
    return neighbor_walls


def build_perimeter_wall(board):
    border = {(0, y) for y in range(display.BOARD_HEIGHT)}
    border |= {(display.BOARD_WIDTH - 1, y) for y in range(display.BOARD_HEIGHT)}
    border |= {(x, 0) for x in range(display.BOARD_WIDTH)}
    border |= {(x, display.BOARD_HEIGHT - 1) for x in range(display.BOARD_WIDTH)}

    for x, y in border:
        board.retile(x, y, create.tile.wall)


def player_hears(pos: cmp.Position):
    """true if the source is close enough for player to hear"""
    player_cmp = ecs.Query(cmp.Player).val

    player_pos = player_position()
    dist_to_player = euclidean_distance(player_pos, pos)
    return dist_to_player < player_cmp.perception_radius


def new_map():
    old_map = ecs.Query(cmp.Position).exclude(cmp.Player, cmp.Crosshair)
    for to_del, _ in old_map:
        esper.delete_entity(to_del, immediate=True)

    game_meta = ecs.Query(cmp.GameMeta).first()

    def new_map_info():
        depth = 0
        if esper.has_component(game_meta, cmp.MapInfo):
            depth = esper.component_for_entity(game_meta, cmp.MapInfo).depth
            esper.remove_component(game_meta, cmp.MapInfo)
        mood = display.Mood.shuffle()
        wall = random.choice([display.Glyph.WALL1, display.Glyph.WALL2])
        bwall = random.choice([display.Glyph.BWALL1])  # , display.Glyph.BWALL2
        mi = cmp.MapInfo(mood=mood, wall_glyph=wall, bwall_glyph=bwall, depth=depth + 1)
        esper.add_component(game_meta, mi)

    new_map_info()

    game_meta_cmp = esper.component_for_entity(game_meta, cmp.GameMeta)
    game_meta_cmp.board = Board()
    maps = [Dungeon, DrunkenWalk, Maze]  # BSPDungeon, TestDungeon
    mapgen_func = random.choice(maps)
    mapgen_func(game_meta_cmp.board)
    game_meta_cmp.board.build_entity_cache()


class Dungeon:
    board: Board
    rooms: list[RectangularRoom]
    centers: list[cmp.Position]

    def __init__(self, board: Board):
        self.board = board
        self.rooms = []
        self.centers = []
        self.build()

    def build(self, max_rooms=30, max_rm_siz=10, min_rm_siz=6):
        self.board.fill()
        for _ in range(max_rooms):
            room_width = random.randint(min_rm_siz, max_rm_siz)
            room_height = random.randint(min_rm_siz, max_rm_siz)

            if room := self.make_room(room_width, room_height):
                self.rooms.append(room)

        last_center = self.rooms[-1].center
        self.board.retile(last_center.x, last_center.y, create.tile.stairs)

    def make_room(self, width: int, height: int):
        x = random.randint(0, display.BOARD_WIDTH - width - 1)
        y = random.randint(0, display.BOARD_HEIGHT - height - 1)

        room = RectangularRoom(x, y, width, height)
        if any(intersects(self.board, room, r) for r in self.rooms):
            return  # This room intersects, so go to the next attempt

        for cell in self.board.as_sequence(*room.inner):
            pos = esper.component_for_entity(cell, cmp.Position)
            self.board.retile(pos.x, pos.y, create.tile.floor)

        if len(self.rooms) == 0:  # start player in first room
            pos = player_position()
            pos.x, pos.y = room.center.x, room.center.y
        else:  # All rooms after the first get one tunnel and enemy
            end_ctr = get_closest_pair([room.center], self.centers)[1]
            idx = self.centers.index(end_ctr)
            connect_rooms(room, self.rooms[idx])
            self.populate(room)

        self.centers.append(room.center)
        return room

    def populate(self, room: RectangularRoom):
        """fill a room with pieces"""
        for _ in range(random.randint(1, 3)):
            npcs = [
                create.npc.bat,
                create.npc.skeleton,
                create.npc.warlock,
            ]
            weights = [3, 2, 1]
            npc_gen = random.choices(npcs, weights)[0]
            npc_gen(room.get_random_pos())
        item = random.choice(
            [create.item.spike_trap, create.item.potion, create.item.scroll]
        )
        item(room.get_random_pos())


class Cave:
    board: Board

    def __init__(self, board: Board):
        self.board = board
        self.build()

    def create_gaps(self):
        for cell in self.board.as_sequence():
            if not random.randint(0, 1):
                cell_pos = esper.component_for_entity(cell, cmp.Position)
                self.board.retile(*cell_pos.as_tuple, create.tile.floor)

    def horizontal_blanking(self):
        """big gap in the middle to islands don't form"""
        x_slice = slice(3, display.BOARD_WIDTH - 3)
        y_slice = slice(display.CENTER_H - 1, display.CENTER_H + 2)
        for cell in self.board.as_sequence(x_slice, y_slice):
            player_pos = esper.component_for_entity(cell, cmp.Position)
            self.board.retile(*player_pos.as_tuple, create.tile.floor)

    def automata(self):
        neighbours = matrix(display.BOARD_WIDTH, display.BOARD_HEIGHT, 0)
        cell_autamata_passes = 4
        for _ in range(cell_autamata_passes):
            for cell in self.board.as_sequence():
                player_pos = esper.component_for_entity(cell, cmp.Position)
                wall_count = count_neighbors(self.board, *player_pos)
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
                    self.board.set_cell(x, y, tile)

    def populate(self):
        player_pos = player_position()

        valid_spawns = []
        while len(valid_spawns) < 20:
            x = random.randint(0, display.BOARD_WIDTH - 1)
            y = random.randint(0, display.BOARD_HEIGHT - 1)
            cell = self.board.cells[x][y]
            pos = esper.component_for_entity(cell, cmp.Position)
            wall_count = count_neighbors(self.board, *pos)
            if wall_count == 0:
                dist = math.dist(player_pos.as_tuple, (x, y))
                valid_spawns.append([dist, pos])
        valid_spawns = sorted(valid_spawns, key=lambda x: x[0])
        stair_pos = valid_spawns[-1][1]
        self.board.retile(stair_pos.x, stair_pos.y, create.tile.stairs)

        spawn_table = {
            create.item.spike_trap: 3,
            create.item.potion: 2,
            create.item.scroll: 1,
            create.npc.bat: 5,
            create.npc.goblin: 3,
            create.npc.warlock: 1,
        }
        for _, pos in valid_spawns[:-1]:
            spawn = math_util.rand_from_table(spawn_table)
            self.board.retile(pos.x, pos.y, create.tile.floor)
            new_pos = cmp.Position(pos.x, pos.y)
            spawn(new_pos)

    def build(self):
        self.board.fill()
        self.create_gaps()
        self.horizontal_blanking()

        self.automata()

        build_perimeter_wall(self.board)
        # TODO: the 3 cells closes to corner should be wall too

        player_pos = player_position()
        player_pos.x = display.BOARD_WIDTH // 2
        player_pos.y = display.BOARD_HEIGHT // 2

        self.populate()


class Maze:
    board: Board

    def __init__(self, board: Board):
        self.board = board

        blueprint, seen, dead_ends = self.make_blueprint()
        self.build(blueprint, seen)
        self.populate(seen, dead_ends)

    def hydrate(self, x):
        return (x * 2) - 1

    def dehydrate(self, x):
        return (x + 1) // 2

    def make_blueprint(self):
        """
        1/4 scale blueprint for maze
        every every odd coord pair is a wall
        we start at a random location and pick a neighbor at random
        add current space to backtrack stack
        break wall between current and neighbor. Add both to visited set
        then pick an unvisited neighbor and repeat
        when there are no neighbors, pop stack and try again for that space
        """
        end_x = (display.BOARD_WIDTH // 2) + 1
        end_y = (display.BOARD_HEIGHT // 2) + 1
        blueprint = matrix(end_x, end_y, 1)

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
                if x > 0 and x < end_x and y > 0 and y < end_y:
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

        dead_ends = []
        for x in range(end_x):
            for y in range(end_y):
                if [x, y] in (seen[-1], seen[0]):
                    continue
                if x % 2 == 1 and y % 2 == 1:
                    walls = 0
                    for ox, oy in [(-1, 0), (1, 0), (0, 1), (0, -1)]:
                        walls += blueprint[x + ox][y + oy]
                    if walls == 3:
                        dead_ends.append([x, y])

        return blueprint, seen, dead_ends

    def place_from_table(self, spawn_table, coords, odds):
        for x, y in coords:
            if not random.randint(0, odds):
                continue

            offset = random.choice([(0, 0), (1, 0), (0, 1), (1, 1)])
            spawn_x = self.hydrate(x) + offset[0]
            spawn_y = self.hydrate(y) + offset[1]
            pos = cmp.Position(x=spawn_x, y=spawn_y)

            spawn = math_util.rand_from_table(spawn_table)
            spawn(pos)

    def build(self, blueprint, seen):
        self.board.fill()
        player_pos = player_position()

        player_pos.x, player_pos.y = map(self.hydrate, seen[-1])
        stair_x, stair_y = map(self.hydrate, seen[0])

        for cell in self.board.as_sequence():
            pos = esper.component_for_entity(cell, cmp.Position)
            bx, by = map(self.dehydrate, pos.as_tuple)
            if blueprint[bx][by]:
                cell = create.tile.wall(*pos)
            else:
                cell = create.tile.floor(*pos)
            self.board.set_cell(pos.x, pos.y, cell)
        self.board.retile(stair_x, stair_y, create.tile.stairs)

    def populate(self, seen, dead_ends):
        spawn_table = {
            create.item.spike_trap: 3,
            create.npc.bat: 5,
            create.npc.goblin: 3,
            create.npc.warlock: 1,
        }

        self.place_from_table(spawn_table, seen[1:-1], 2)
        spawn_table = {
            create.item.potion: 2,
            create.item.scroll: 1,
        }
        self.place_from_table(spawn_table, dead_ends, 2)


class BSPDungeon:
    board: Board

    def __init__(self, board: Board):
        self.board = board
        self.build()

    def connect(self, tree, bsp, node):
        node1, node2 = node.children
        leaf1 = tree[bsp.find_node(node1.x, node1.y)]
        leaf2 = tree[bsp.find_node(node2.x, node2.y)]

        # TODO: tunnel could be better. we want to only connect adjacent rooms
        connect_rooms(leaf1, leaf2)

    def room_from_node(self, node) -> RectangularRoom:
        min_size = 5  # Minimum size for both width and height
        max_x = node.width - min_size  # Maximum valid x-coordinate
        max_y = node.height - min_size  # Maximum valid y-coordinate

        # Generate random values within bounds
        start_x = random.randint(0, max_x)
        start_y = random.randint(0, max_y)
        width = math_util.biased_randint(node.width - start_x, min_size)
        height = math_util.biased_randint(node.height - start_y, min_size)
        room = RectangularRoom(node.x + start_x, node.y + start_y, width, height)
        return room

    def build(self):
        self.board.fill()
        bsp = tcod.bsp.BSP(x=0, y=0, width=BOARD_MAX, height=BOARD_MAX)
        bsp.split_recursive(
            depth=5,
            min_width=5,
            min_height=5,
            max_horizontal_ratio=1.5,
            max_vertical_ratio=1.5,
        )

        tree = {}
        # In pre order, leaf nodes are visited before
        # the nodes that connect them.
        for node in bsp.post_order():
            if node.children:
                self.connect(tree, bsp, node)
            else:
                room = self.room_from_node(node)

                tree[node] = room
                for cell in self.board.as_sequence(*room.inner):
                    pos = esper.component_for_entity(cell, cmp.Position)
                    self.board.retile(pos.x, pos.y, create.tile.floor)
        rooms = list(tree.values())

        start_room = random.choice(rooms)
        ppos = player_position()
        ppos.x, ppos.y = start_room.center.x, start_room.center.y

        for room in tree.values():
            self.populate(room)

        stair_pos = random.choice(rooms).get_random_pos()
        # do we wanna make sure start and stair rooms are further?
        self.board.retile(stair_pos.x, stair_pos.y, create.tile.stairs)

    def populate(self, room: RectangularRoom):
        """fill a room with pieces"""
        for _ in range(random.randint(1, 3)):
            npcs = [
                create.npc.bat,
                create.npc.skeleton,
                create.npc.warlock,
            ]
            weights = [3, 2, 1]
            npc_gen = random.choices(npcs, weights)[0]
            npc_gen(room.get_random_pos())
        item = random.choice(
            [create.item.spike_trap, create.item.potion, create.item.scroll]
        )
        item(room.get_random_pos())


class TestDungeon:
    board: Board

    def __init__(self, board: Board):
        self.board = board
        self.build()

    def build(self):
        """one room, one enemy, one item"""
        self.board.fill()
        room_x = display.BOARD_WIDTH // 2
        room_y = display.BOARD_HEIGHT // 2
        new_room = RectangularRoom(room_x, room_y, 10, 10)
        for cell in self.board.as_sequence(*new_room.inner):
            pos = esper.component_for_entity(cell, cmp.Position)
            self.board.retile(pos.x, pos.y, create.tile.floor)

        pos = player_position()
        pos.x, pos.y = new_room.center.x, new_room.center.y
        create.npc.cyclops(new_room.get_random_pos())
        for _ in range(20):
            create.item.grass(new_room.get_random_pos())
        create.item.potion(new_room.get_random_pos())
        create.item.scroll(new_room.get_random_pos())
        self.board.build_entity_cache()


class DrunkenWalk:
    board: Board

    def __init__(self, board: Board):
        self.board = board
        path = self.build()
        self.populate(path)

    def build(self):
        """
        Save visited in a stack
        only move onto walls
        if no walls, pop stack
        """
        self.board.fill()

        x = random.randint(1, BOARD_MAX)
        y = random.randint(1, BOARD_MAX)

        player_pos = player_position()
        player_pos.x, player_pos.y = x, y

        self.board.retile(x, y, create.tile.floor)
        floor_goal = 1000
        path = [(x, y)]

        def get_walkable_wall(x, y):
            """find a cardinal step with a non-baorder wall"""
            offsets = [(-1, 0), (0, -1), (0, 1), (1, 0)]
            for dx, dy in random.sample(offsets, k=4):
                new_x, new_y = x + dx, y + dy
                if {new_x, new_y} & {0, BOARD_MAX}:
                    return None
                # without this next check we get caverns
                if count_neighbors(self.board, new_x, new_y) < 4:
                    return None
                cell = self.board.get_cell(new_x, new_y)
                if esper.has_component(cell, cmp.Wall):
                    return new_x, new_y
            return None

        for _ in range(floor_goal):
            nxt = get_walkable_wall(x, y)
            while nxt is None:
                nxt = get_walkable_wall(*path.pop())
            x, y = nxt
            self.board.retile(x, y, create.tile.floor)
            path.append(nxt)

        self.board.retile(path[-1][0], path[-1][1], create.tile.stairs)
        return path

    def populate(self, path):
        map_info = ecs.Query(cmp.GameMeta).cmp(cmp.MapInfo)
        spawn_goal = 20 + map_info.depth

        spawn_table = {
            create.item.spike_trap: 3,
            create.item.potion: 2,
            create.item.scroll: 1,
            create.npc.bat: 5,
            create.npc.goblin: 3,
            create.npc.warlock: 1,
        }

        floor = path[:-1]
        for x, y in random.sample(floor, k=spawn_goal):
            spawn = math_util.rand_from_table(spawn_table)
            new_pos = cmp.Position(x, y)
            spawn(new_pos)
