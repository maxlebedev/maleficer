import random
from dataclasses import dataclass

import esper
import tcod
from tcod import libtcodpy
from tcod.map import compute_fov

import board
import components as cmp
import display
import event
import input
import scene
import typ


@dataclass
class MovementProcessor(esper.Processor):
    board: board.Board

    def process(self):
        while event.Queues.movement:
            movement = event.Queues.movement.pop()
            ent = movement.source
            move_x = movement.x
            move_y = movement.y
            if not esper.entity_exists(ent): # entity intends to move, but dies first
                continue

            pos = esper.component_for_entity(ent, cmp.Position)
            new_x = pos.x + move_x
            new_y = pos.y + move_y
            # Note: as written, walking into a wall consumes a turn
            move = True
            self.board.build_entity_cache()  # expensive, but okay
            for target in self.board.entities[new_x][new_y]:
                if esper.has_component(target, cmp.Blocking):
                    move = False
                    src_is_enemy = esper.has_component(ent, cmp.Enemy)
                    target_is_harmable = esper.has_component(target, cmp.Actor)
                    if src_is_enemy and target_is_harmable:
                        event.Queues.damage.append(event.Damage(ent, target, 1))

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
                esper.delete_entity(damage.target)
                # crashes if player gets deleted
        # this probably not where we process death
        # death can potentially happen without damage

@dataclass
class InputEventProcessor(esper.Processor):
    action_map = {}

    def exit(self):
        raise SystemExit()

    def process(self):
        action = None
        while not action:
            for input_event in tcod.event.wait():
                # if we ever have other events we care abt, we can dispatch by type
                if not isinstance(input_event, tcod.event.KeyDown):
                    continue
                if input_event.sym in self.action_map:
                    func, args = self.action_map[input_event.sym]
                    action = func(*args)
        # TODO: this is a code smell. "action" holds both the release for this loop, and the signal for us to queue a movement event. The queueing should perhaps happen in func
        if isinstance(action, event.Movement):
            event.Queues.movement.append(action)


@dataclass
class GameInputEventProcessor(InputEventProcessor):
    def __init__(self):
        player, _ = esper.get_component(cmp.Player)[0]
        # to_target = (esper.dispatch_event, ["target"])
        self.action_map = {
            input.KEYMAP[input.Input.MOVE_DOWN]: (event.Movement, [player, 0, 1]),
            input.KEYMAP[input.Input.MOVE_LEFT]: (event.Movement, [player, -1, 0]),
            input.KEYMAP[input.Input.MOVE_UP]: (event.Movement, [player, 0, -1]),
            input.KEYMAP[input.Input.MOVE_RIGHT]: (event.Movement, [player, 1, 0]),
            input.KEYMAP[input.Input.ESC]: (scene.to_phase, [scene.Phase.menu]),
            # input.KEYMAP[input.Input.ONE]: to_target,
        }


@dataclass
class NPCProcessor(esper.Processor):

    def process(self):
        for entity, _ in esper.get_component(cmp.Enemy):
            dir = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0), (0, 0)])
            if dir == (0, 0):
                continue
            move = event.Movement(entity, *dir)
            event.Queues.movement.append(move)
            # consider the move processor potentially sending a Bump event,
            # and then reading that event (this means this proc runs twice?)
            # this lets each NPC decide what behavior to have on a bump


@dataclass
class BoardRenderProcessor(esper.Processor):
    console: tcod.console.Console
    context: tcod.context.Context
    board: board.Board

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
        self.console.print(2, 2, "ABCDEFGHIJKLM")
        self.console.print(2, 3, "NOPQUSTUVWXYZ")
        self.console.print(2, 4, "0123456789.")
        _, (_, actor) = esper.get_components(cmp.Player, cmp.Actor)[0]
        self.render_bar(1, 5, actor.hp, 10, display.PANEL_WIDTH - 2)
        # right panel
        self.console.draw_frame(x=display.R_PANEL_START, **panel_params)
        for i, message in enumerate(event.Log.messages):
            self.console.print(1 + display.R_PANEL_START, 1 + i, message)

    def _apply_lighting(self, cell_rgbs, in_fov) -> list[list[typ.CELL_RGB]]:
        """display cells in fov with lighting, explored without, and hide the rest"""
        for x, col in enumerate(cell_rgbs):
            for y, (glyph, fgcolor, _) in enumerate(col):
                cell = self.board.get_cell(x, y)
                if not cell:
                    continue
                if in_fov[x][y]:
                    self.board.explored.add(cell)
                    brighter = display.brighter(fgcolor, scale=100)
                    cell_rgbs[x][y] = (glyph, brighter, display.Color.CANDLE)
                elif cell in self.board.explored:
                    cell_rgbs[x][y] = (glyph, fgcolor, display.Color.BLACK)
                else:
                    cell_rgbs[x][y] = (glyph, display.Color.BLACK, display.Color.BLACK)
        return cell_rgbs

    def process(self):
        self.console.clear()
        self._draw_panels()

        cell_rgbs = [list(map(self.board.as_rgb, row)) for row in self.board.cells]

        transparency = self.board.as_transparency()
        _, (_, pos) = esper.get_components(cmp.Player, cmp.Position)[0]
        algo = libtcodpy.FOV_SHADOW
        in_fov = compute_fov(transparency, (pos.x, pos.y), radius=4, algorithm=algo)

        drawable_entities = esper.get_components(cmp.Position, cmp.Visible)
        for entity, (pos, vis) in drawable_entities:
            if esper.has_component(entity, cmp.Cell) or not in_fov[pos.x][pos.y]:
                continue
            cell_rgbs[pos.x][pos.y] = (vis.glyph, vis.color, vis.bg_color)

        cell_rgbs = self._apply_lighting(cell_rgbs, in_fov)

        startx, endx = (display.PANEL_WIDTH, display.R_PANEL_START)
        starty, endy = (0, display.BOARD_HEIGHT)
        self.console.rgb[startx:endx, starty:endy] = cell_rgbs

        self.context.present(self.console)  # , integer_scaling=True

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
            input.KEYMAP[input.Input.SELECT]: (scene.to_phase, [scene.Phase.board]),
        }

@dataclass
class TargetInputEventProcessor(InputEventProcessor):
    def __init__(self):
        to_game_scene = (esper.dispatch_event, ["change_scene", scene.State.GAME])
        self.action_map = {
            input.KEYMAP[input.Input.ESC]: (self.exit, []),
            input.KEYMAP[input.Input.SELECT]: to_game_scene,
        }
