from dataclasses import dataclass
from tcod.map import compute_fov

import esper
import tcod

import actions
import board
import components as cmp
import display
import input
import random


@dataclass
class MovementProcessor(esper.Processor):
    board: board.Board

    def process(self):
        for ent, (move, pos) in esper.get_components(cmp.Moving, cmp.Position):
            new_x = pos.x + move.x
            new_y = pos.y + move.y
            # Note: as written, walking into a wall consumes a turn
            move = True
            self.board.build_entity_cache() # expensive, but okay
            for target in self.board.entities[new_x][new_y]:
                if esper.has_component(target, cmp.Blocking):
                    move = False

            if move:
                pos.x = new_x
                pos.y = new_y
                self.board.entities[new_x][new_y].add(ent)
            esper.remove_component(ent, cmp.Moving)


# TODO: unclear delineation w EventHandler
# currently EventHandler -> Action -> EventProcessor. Can almost certainly be simplified
@dataclass
class EventProcessor(esper.Processor):
    event_handler: input.EventHandler

    def process(self):
        player, _ = esper.get_component(cmp.Player)[0]
        player_turn = True
        while player_turn:
            for event in tcod.event.wait():
                action = self.event_handler.dispatch(event)
                if action and isinstance(action, actions.MovementAction):
                    esper.add_component(player, cmp.Moving(x=action.dx, y=action.dy))
                    player_turn = False

@dataclass
class NPCProcessor(esper.Processor):

    def process(self):
        for entity, _ in esper.get_component(cmp.NPC):
            dir = random.choice([(0,1), (0,-1), (1,0), (-1,0), (0,0)])
            esper.add_component(entity, cmp.Moving(x=dir[0], y=dir[1]))


@dataclass
class RenderProcessor(esper.Processor):
    console: tcod.console.Console
    context: tcod.context.Context
    board: board.Board

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
        # right panel
        self.console.draw_frame(x=display.R_PANEL_START, **panel_params)

    # -> tuple[list[list[tuple[int, display.RGB, display.RGB]]], tuple]
    def _apply_lighting(self, cell_rgbs):
        transparency = self.board.as_transparency()
        _, (_, pos) = esper.get_components(cmp.Player, cmp.Position)[0]
        in_fov = compute_fov(transparency, (pos.x, pos.y), radius=8)

        for x, col in enumerate(cell_rgbs):
            for y, rgb_cell in enumerate(col):
                # 3 cases.
                # in fov, display with lighting
                # explored, display black
                # else display nothing
                cell = self.board.get_cell(x, y)
                if in_fov[x][y] and cell:
                    self.board.explored.add(cell)
                    brighter = display.brighter(rgb_cell[1], scale=100)
                    cell_rgbs[x][y] = (rgb_cell[0], brighter, display.DGREY)
                elif not in_fov[x][y]:
                    if cell in self.board.explored:
                        cell_rgbs[x][y] = (rgb_cell[0], rgb_cell[1], display.BLACK)
                    else:
                        cell_rgbs[x][y] = (rgb_cell[0], display.BLACK, display.BLACK)
        return cell_rgbs, in_fov

    def process(self):
        self.console.clear()
        self._draw_panels()


        cell_rgbs = [list(map(self.board.as_rgb, row)) for row in self.board.cells]
        cell_rgbs, in_fov = self._apply_lighting(cell_rgbs)

        startx, endx = (display.PANEL_WIDTH, display.R_PANEL_START)
        starty, endy = (0, display.BOARD_HEIGHT)
        self.console.rgb[startx:endx, starty:endy] = cell_rgbs

        drawable_entities = esper.get_components(cmp.Position, cmp.Visible)
        for entity,(pos, vis)  in drawable_entities:
            if esper.has_component(entity, cmp.Cell) or not in_fov[pos.x][pos.y]:
                continue
            x = pos.x + display.PANEL_WIDTH
            self.console.rgb[x, pos.y] = (vis.glyph, vis.color, vis.bg_color)
            # self.console.print(x, pos.y, vis.glyph, fg=vis.color)

        self.context.present(self.console)  # , integer_scaling=True
