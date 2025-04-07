import random
from dataclasses import dataclass

import esper
import tcod
from tcod import libtcodpy
from tcod.map import compute_fov

import components as cmp
import display
import event
import input
import location
import scene
import typ
import ecs


@dataclass
class MovementProcessor(esper.Processor):
    board: location.Board

    def process(self):
        while event.Queues.movement:
            movement = event.Queues.movement.pop()
            ent = movement.source
            move_x = movement.x
            move_y = movement.y
            if not esper.entity_exists(ent):  # entity intends to move, but dies first
                continue

            pos = esper.component_for_entity(ent, cmp.Position)
            new_x = pos.x + move_x
            new_y = pos.y + move_y
            # Note: as written, walking into a wall consumes a turn
            move = True
            self.board.build_entity_cache()  # expensive, but okay
            for target in self.board.entities[new_x][new_y]:
                ent_is_actor = esper.has_component(ent, cmp.Actor)
                if ent_is_actor and esper.has_component(target, cmp.Blocking):
                    move = False
                    src_is_enemy = esper.has_component(ent, cmp.Enemy)
                    target_is_harmable = esper.has_component(target, cmp.Actor)
                    if src_is_enemy and target_is_harmable:
                        event.Damage(ent, target, 1)
                ent_is_player = esper.has_component(ent, cmp.Player)
                target_is_collectable = esper.has_component(target, cmp.Collectable)
                if ent_is_player and target_is_collectable:
                    esper.remove_component(target, cmp.Position)
                    esper.add_component(target, cmp.InInventory)
                    print(f"player picked up an item")
                    # TODO: now print that on a side pane
                    # oneshot call some collectable processor?

            if move:
                pos.x = new_x
                pos.y = new_y
                self.board.entities[new_x][new_y].add(ent)


@dataclass
class DamageProcessor(esper.Processor):
    def process(self):
        while event.Queues.damage:
            damage = event.Queues.damage.pop()
            if not all(map(esper.entity_exists, [damage.target, damage.source])):
                # if either entity doesn't exist anymore, damage fizzles
                continue

            actor = esper.component_for_entity(damage.target, cmp.Actor)
            actor.hp -= damage.amount

            src_actor = esper.component_for_entity(damage.source, cmp.Actor)
            message = f"{src_actor.name} deals {damage.amount} to {actor.name}"
            print(message)
            event.Log.append(message)

            if actor.hp <= 0:
                message = f"{actor.name} dies"
                print(message)
                event.Log.append(message)
                esper.delete_entity(damage.target, immediate=True)
                # crashes if player gets deleted
        # this probably not where we process death
        # death can potentially happen without damage


@dataclass
class InputEventProcessor(esper.Processor):
    action_map = {}

    def exit(self):
        raise SystemExit()

    def process(self):
        listen = True
        while listen:
            for input_event in tcod.event.wait():
                # if we ever have other events we care abt, we can dispatch by type
                if not isinstance(input_event, tcod.event.KeyDown):
                    continue
                if input_event.sym in self.action_map:
                    func, args = self.action_map[input_event.sym]
                    func(*args)
                    listen = False


@dataclass
class GameInputEventProcessor(InputEventProcessor):
    def __init__(self):
        player, _ = esper.get_component(cmp.Player)[0]
        self.action_map = {
            input.KEYMAP[input.Input.MOVE_DOWN]: (event.Movement, [player, 0, 1]),
            input.KEYMAP[input.Input.MOVE_LEFT]: (event.Movement, [player, -1, 0]),
            input.KEYMAP[input.Input.MOVE_UP]: (event.Movement, [player, 0, -1]),
            input.KEYMAP[input.Input.MOVE_RIGHT]: (event.Movement, [player, 1, 0]),
            input.KEYMAP[input.Input.ESC]: (scene.to_phase, [scene.Phase.menu]),
            input.KEYMAP[input.Input.ONE]: (self.to_target, []),
        }

    def to_target(self):
        player_pos = location.player_position()
        _, (_, xhair_pos) = esper.get_components(cmp.Crosshair, cmp.Position)[0]
        xhair_pos.x, xhair_pos.y = player_pos.x, player_pos.y
        scene.to_phase(scene.Phase.target)


@dataclass
class NPCProcessor(esper.Processor):
    def process(self):
        for entity, _ in esper.get_component(cmp.Wander):
            dir = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0), (0, 0)])
            if dir == (0, 0):
                continue
            event.Movement(entity, *dir)

        player_pos = location.player_position()
        for entity, _ in esper.get_component(cmp.Melee):
            epos = esper.component_for_entity(entity, cmp.Position)
            melee = esper.component_for_entity(entity, cmp.Melee)
            dist_to_player = location.euclidean_distance(player_pos, epos)
            if dist_to_player > melee.radius:
                continue
            # Naive pathfinding. Does not deal with corners well
            if player_pos.x > epos.x:
                event.Movement(entity, x=1, y=0)
            elif player_pos.y > epos.y:
                event.Movement(entity, x=0, y=1)
            elif player_pos.x < epos.x:
                event.Movement(entity, x=-1, y=0)
            elif player_pos.y < epos.y:
                event.Movement(entity, x=0, y=-1)


@dataclass
class RenderProcessor(esper.Processor):
    console: tcod.console.Console
    context: tcod.context.Context

    def render_bar(self, x: int, y: int, curr: int, maximum: int, total_width: int):
        bar_width = int(curr / maximum * total_width)
        bg = display.Color.BAR_EMPTY
        self.console.draw_rect(x=x, y=y, width=total_width, height=1, ch=1, bg=bg)

        if bar_width > 0:
            bg = display.Color.BAR_FILLED
            self.console.draw_rect(x=x, y=y, width=bar_width, height=1, ch=1, bg=bg)

        text = f"HP: {curr}/{maximum}"
        self.console.print(x=x, y=y, string=text, fg=display.Color.DGREY)

    def _draw_panels(self):
        panel_params = {
            "y": 0,
            "width": display.PANEL_WIDTH,
            "height": display.PANEL_HEIGHT,
            "decoration": (
                display.Glyph.FRAME1,
                display.Glyph.FRAME2,
                display.Glyph.FRAME3,
                display.Glyph.FRAME4,
                display.Glyph.NONE,
                display.Glyph.FRAME6,
                display.Glyph.FRAME7,
                display.Glyph.FRAME8,
                display.Glyph.FRAME9,
            ),
        }

        # left panel
        self.console.draw_frame(x=0, **panel_params)
        _, (_, actor) = esper.get_components(cmp.Player, cmp.Actor)[0]
        self.render_bar(1, 1, actor.hp, actor.max_hp, display.PANEL_WIDTH - 2)
        # right panel
        self.console.draw_frame(x=display.R_PANEL_START, **panel_params)
        for i, message in enumerate(event.Log.messages):
            self.console.print(1 + display.R_PANEL_START, 1 + i, message)

    def _apply_lighting(self, gameboard, cell_rgbs, in_fov) -> list[list[typ.CELL_RGB]]:
        """display cells in fov with lighting, explored without, and hide the rest"""
        for x, col in enumerate(cell_rgbs):
            for y, (glyph, fgcolor, _) in enumerate(col):
                cell = gameboard.get_cell(x, y)
                if not cell:
                    continue
                if in_fov[x][y]:
                    gameboard.explored.add(cell)
                    brighter = display.brighter(fgcolor, scale=100)
                    cell_rgbs[x][y] = (glyph, brighter, display.Color.CANDLE)
                elif cell in gameboard.explored:
                    cell_rgbs[x][y] = (glyph, fgcolor, display.Color.BLACK)
                else:
                    cell_rgbs[x][y] = (glyph, display.Color.BLACK, display.Color.BLACK)
        return cell_rgbs

    def _get_fov(self, board: location.Board):
        transparency = board.as_transparency()
        pos = location.player_position()
        algo = libtcodpy.FOV_SHADOW
        fov = compute_fov(transparency, (pos.x, pos.y), radius=4, algorithm=algo)
        return fov

    def present(self, cell_rgbs):
        startx, endx = (display.PANEL_WIDTH, display.R_PANEL_START)
        starty, endy = (0, display.BOARD_HEIGHT)
        self.console.rgb[startx:endx, starty:endy] = cell_rgbs
        self.context.present(self.console)  # , integer_scaling=True



@dataclass
class BoardRenderProcessor(RenderProcessor):
    console: tcod.console.Console
    context: tcod.context.Context
    board: location.Board

    def process(self):
        self.console.clear()
        self._draw_panels()

        cell_rgbs = [list(map(self.board.as_rgb, row)) for row in self.board.cells]

        in_fov = self._get_fov(self.board)

        drawable_entities = ecs.Query().filter(cmp.Position, cmp.Visible)
        nonwall_drawables = drawable_entities.exclude(cmp.Cell).get()
        for _, (pos, vis) in nonwall_drawables:
            if not in_fov[pos.x][pos.y]:
                continue
            cell_rgbs[pos.x][pos.y] = (vis.glyph, vis.color, vis.bg_color)

        cell_rgbs = self._apply_lighting(self.board, cell_rgbs, in_fov)
        self.present(cell_rgbs)



@dataclass
class MenuRenderProcessor(esper.Processor):
    context: tcod.context.Context
    console: tcod.console.Console

    def process(self):
        self.console.clear()
        x = display.PANEL_WIDTH + (display.BOARD_WIDTH // 2)
        y = display.BOARD_HEIGHT // 2
        self.console.print(x, y, "WELCOME TO MALEFICER", alignment=libtcodpy.CENTER)
        self.context.present(self.console)  # , integer_scaling=True


@dataclass
class MenuInputEventProcessor(InputEventProcessor):
    def __init__(self):
        self.action_map = {
            input.KEYMAP[input.Input.ESC]: (self.exit, []),
            input.KEYMAP[input.Input.SELECT]: (scene.to_phase, [scene.Phase.level]),
        }


@dataclass
class TargetInputEventProcessor(InputEventProcessor):
    board: location.Board

    def __init__(self, board):
        self.board = board
        crosshair, _ = esper.get_component(cmp.Crosshair)[0]
        to_level = (scene.to_phase, [scene.Phase.level])

        self.action_map = {
            input.KEYMAP[input.Input.MOVE_DOWN]: (event.Movement, [crosshair, 0, 1]),
            input.KEYMAP[input.Input.MOVE_LEFT]: (event.Movement, [crosshair, -1, 0]),
            input.KEYMAP[input.Input.MOVE_UP]: (event.Movement, [crosshair, 0, -1]),
            input.KEYMAP[input.Input.MOVE_RIGHT]: (event.Movement, [crosshair, 1, 0]),
            input.KEYMAP[input.Input.ESC]: to_level,
            input.KEYMAP[input.Input.SELECT]: (self.deal_damage, [crosshair]),
        }

    def deal_damage(self, positioned_entity: int):
        player, _ = esper.get_component(cmp.Player)[0]
        pos = esper.component_for_entity(positioned_entity, cmp.Position)
        self.board.build_entity_cache()  # expensive, but okay
        for target in self.board.entities[pos.x][pos.y]:
            if esper.has_component(target, cmp.Actor):
                event.Damage(player, target, 1)
        scene.to_phase(scene.Phase.level, NPCProcessor)


@dataclass
class TargetRenderProcessor(RenderProcessor):
    console: tcod.console.Console
    context: tcod.context.Context
    board: location.Board

    def process(self) -> None:
        self.console.clear()
        self._draw_panels()

        cell_rgbs = [list(map(self.board.as_rgb, row)) for row in self.board.cells]

        in_fov = self._get_fov(self.board)

        drawable_entities = ecs.Query().filter(cmp.Position, cmp.Visible)
        nonwall_drawables = drawable_entities.exclude(cmp.Cell).get()
        for _, (pos, vis) in nonwall_drawables:
            if not in_fov[pos.x][pos.y]:
                continue
            cell_rgbs[pos.x][pos.y] = (vis.glyph, vis.color, vis.bg_color)

        cell_rgbs = self._apply_lighting(self.board, cell_rgbs, in_fov)

        drawable_areas = ecs.Query().filter(cmp.Position, cmp.EffectArea).get()
        for _, (pos, aoe) in drawable_areas:
            cell = cell_rgbs[pos.x][pos.y]
            cell_rgbs[pos.x][pos.y] = cell[0], cell[1], aoe.color

        self.present(cell_rgbs)
