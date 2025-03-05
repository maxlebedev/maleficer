from dataclasses import dataclass
from tcod.map import compute_fov

import esper
import tcod

import actions
import board
import components as cmp
import display
import input


@dataclass
class MovementProcessor(esper.Processor):
    board: board.Board

    def process(self):
        for ent, (move, pos) in esper.get_components(cmp.Moving, cmp.Position):
            new_x = pos.x + move.x
            new_y = pos.y + move.y
            # move only if the target tile is not blocking
            target_cell = self.board.get_cell(new_x, new_y)
            # Note: as written, when we have a turn system, walking into a wall consumes a turn
            if target_cell and not esper.has_component(target_cell, cmp.Blocking):
                pos.x = new_x
                pos.y = new_y
            esper.remove_component(ent, cmp.Moving)


# TODO: unclear delineation w EventHandler
# currently EventHandler -> Action -> EventProcessor. Can almost certainly be simplified
@dataclass
class EventProcessor(esper.Processor):
    event_handler: input.EventHandler

    def process(self):
        player, _ = esper.get_component(cmp.Player)[0]
        for event in tcod.event.wait():
            action = self.event_handler.dispatch(event)
            if action and isinstance(action, actions.MovementAction):
                esper.add_component(player, cmp.Moving(x=action.dx, y=action.dy))


@dataclass
class RenderProcessor(esper.Processor):
    console: tcod.console.Console
    context: tcod.context.Context
    board: board.Board

    def process(self):
        self.console.clear()

        panel_params = {
            "y": 0,
            "width": display.PANEL_WIDTH,
            "height": display.PANEL_HEIGHT,
            "decoration": "╔═╗║ ║╚═╝",
        }

        # left panel
        self.console.draw_frame(x=0, **panel_params)
        # right panel
        self.console.draw_frame(x=display.R_PANEL_START, **panel_params)

        startx, endx = (display.PANEL_WIDTH, display.R_PANEL_START)
        starty, endy = (0, display.BOARD_HEIGHT)
        # TODO: check if explored first
        cell_rgbs = [list(map(self.board.as_rgb, row)) for row in self.board.cells]

        transparency = self.board.as_transparency()
        _, (_, pos) = esper.get_components(cmp.Player, cmp.Position)[0]
        in_fov = compute_fov(transparency, (pos.x, pos.y), radius=8)

        for x, col in enumerate(cell_rgbs):
            for y, rgb_cell in enumerate(col):
                # 3 cases.
                # in fov, display unedited
                # explored, display black
                # else display nothing
                cell = self.board.get_cell(x, y)
                if in_fov[x][y] and cell:
                    self.board.explored.add(cell)
                elif self.board.get_cell(x, y) in self.board.explored:
                    cell_rgbs[x][y] = (rgb_cell[0], rgb_cell[1], display.BLACK)
                elif not in_fov[x][y]:
                    cell_rgbs[x][y] = (rgb_cell[0], display.BLACK, display.BLACK)

        self.console.rgb[startx:endx, starty:endy] = cell_rgbs

        player_components = esper.get_components(cmp.Player, cmp.Position, cmp.Visible)
        for _, (_, pos, vis) in player_components:
            x = pos.x + display.PANEL_WIDTH
            self.console.print(x, pos.y, vis.glyph, fg=vis.color)

        self.context.present(self.console)  # , integer_scaling=True
