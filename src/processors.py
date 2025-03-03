from functools import partial

import esper
import tcod

import actions
import components as cmp
import display


class MovementProcessor(esper.Processor):
    def process(self):
        for ent, (move, pos) in esper.get_components(cmp.Moving, cmp.Position):
            pos.x += move.x
            pos.y += move.y
            esper.remove_component(ent, cmp.Moving)


# TODO: unclear delineation w EventHandler
class EventProcessor(esper.Processor):
    def __init__(self, event_handler):
        self.event_handler = event_handler

    def process(self):
        player, _ = esper.get_component(cmp.Player)[0]
        for event in tcod.event.wait():
            action = self.event_handler.dispatch(event)
            if action and isinstance(action, actions.MovementAction):
                esper.add_component(player, cmp.Moving(x=action.dx, y=action.dy))


class RenderProcessor(esper.Processor):
    def __init__(self, console, context, board):
        self.console = console
        self.context = context
        self.board = board

    def process(self):
        self.console.clear()

        side_panel = partial(self.console.draw_frame, decoration="╔═╗║ ║╚═╝")

        w = display.PANEL_WIDTH
        h = display.PANEL_HEIGHT
        # left panel
        side_panel(x=0, y=0, width=w, height=h)

        # right panel
        side_panel(x=display.BOARD_END_COORD, y=0, width=w, height=h)

        startx, endx = (display.PANEL_WIDTH, display.BOARD_END_COORD)
        starty, endy = (0, display.BOARD_HEIGHT)
        cell_rgbs = [list(map(self.board.cell_to_rgb, row)) for row in self.board.cells]
        self.console.rgb[startx:endx, starty:endy] = cell_rgbs

        player_components = esper.get_components(cmp.Player, cmp.Position, cmp.Visible)
        for _, (_, pos, vis) in player_components:
            self.console.print(
                pos.x + display.PANEL_WIDTH, pos.y, vis.glyph, fg=vis.color
            )
        self.context.present(self.console)  # , integer_scaling=True
