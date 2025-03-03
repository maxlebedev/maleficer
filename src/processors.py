import esper
import components as cmp
import actions
import tcod
from functools import partial
import display

# TODO: more things need to be here
class MovementProcessor(esper.Processor):
    def process(self):
        for ent, (move, pos) in esper.get_components(cmp.Movement, cmp.Position):
            pos.x += move.x
            pos.y += move.y
            esper.remove_component(ent, cmp.Movement)

# TODO: redundant with event handler?
class EventProcessor(esper.Processor):

    def __init__(self, event_handler):
        self.event_handler = event_handler

    def process(self):
        player, _ = esper.get_component(cmp.Player)[0]
        for event in tcod.event.wait():
            action = self.event_handler.dispatch(event)
            if action and isinstance(action, actions.MovementAction):
                esper.add_component(player, cmp.Movement(x=action.dx, y=action.dy))


class RenderProcessor(esper.Processor):

    def __init__(self, event_handler, console, context):
        self.event_handler = event_handler
        self.console = console
        self.context = context

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
        self.console.rgb[startx:endx, starty:endy] = (ord("."), display.WHITE, display.BLACK)

        player_components = esper.get_components(cmp.Player, cmp.Position, cmp.Visible)
        for _, (_, pos, vis) in player_components:
            self.console.print(pos.x + display.PANEL_WIDTH, pos.y, vis.glyph, fg=vis.color)
        self.context.present(self.console)  # , integer_scaling=True
