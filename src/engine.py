import esper
import tcod
import display

import input_handlers
from input_handlers import Input
import components as cmp
import actions
from typing import Optional

from tcod.context import Context
from tcod.console import Console
from functools import partial


# TODO: I'm not sure if EventHandler wants to be here or in input
class EventHandler(tcod.event.EventDispatch[actions.Action]):
    def __init__(self):
        keymap_path = "keymap.yaml"
        self.keymap = input_handlers.load_keymap(keymap_path)

    def ev_quit(self, event: tcod.event.Quit):
        raise SystemExit()

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[actions.Action]:
        player = esper.get_component(cmp.Player)[0][0]
        action = None
        if self.keymap and not esper.has_component(player, cmp.Movement):
            if event.sym == self.keymap[Input.MOVE_DOWN]:
                action = actions.MovementAction(dx=0, dy=1)
            elif event.sym == self.keymap[Input.MOVE_LEFT]:
                action = actions.MovementAction(dx=-1, dy=0)
            elif event.sym == self.keymap[Input.MOVE_UP]:
                action = actions.MovementAction(dx=0, dy=-1)
            elif event.sym == self.keymap[Input.MOVE_RIGHT]:
                action = actions.MovementAction(dx=1, dy=0)
            elif event.sym == tcod.event.KeySym.ESCAPE:
                raise SystemExit()
        return action


# TODO: this is at odds with the Processors
# engine runs the game loop
class Engine:
    def __init__(self, event_handler: EventHandler):
        self.event_handler = event_handler

    def render(self, console: Console, context: Context) -> None:
        console.clear()

        side_panel = partial(console.draw_frame, decoration="╔═╗║ ║╚═╝")

        w = display.PANEL_WIDTH
        h = display.PANEL_HEIGHT
        # left panel
        side_panel(x=0, y=0, width=w, height=h)

        # right panel
        side_panel(x=display.BOARD_END_COORD, y=0, width=w, height=h)

        startx, endx = (display.PANEL_WIDTH, display.BOARD_END_COORD)
        starty, endy = (0, display.BOARD_HEIGHT)
        console.rgb[startx:endx, starty:endy] = (ord("."), display.WHITE, display.BLACK)

        player_components = esper.get_components(cmp.Player, cmp.Position, cmp.Visible)
        for _, (_, pos, vis) in player_components:
            console.print(pos.x + display.PANEL_WIDTH, pos.y, vis.glyph, fg=vis.color)
        context.present(console)  # , integer_scaling=True
