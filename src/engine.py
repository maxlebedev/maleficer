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
