import esper
import tcod

import actions
import components as cmp
import input_handlers
from input_handlers import Input


# TODO: I'm not sure if EventHandler wants to be here or in input
class EventHandler(tcod.event.EventDispatch[actions.Action]):
    def __init__(self):
        keymap_path = "keymap.yaml"
        self.keymap = input_handlers.load_keymap(keymap_path)
        self.action_map = {
            self.keymap[Input.MOVE_DOWN]: (actions.MovementAction, (0, 1)),
            self.keymap[Input.MOVE_LEFT]: (actions.MovementAction, (-1, 0)),
            self.keymap[Input.MOVE_UP]: (actions.MovementAction, (0, -1)),
            self.keymap[Input.MOVE_RIGHT]: (actions.MovementAction, (1, 0)),
        }

    def ev_quit(self, event: tcod.event.Quit):
        raise SystemExit()

    def ev_keydown(self, event: tcod.event.KeyDown) -> actions.Action | None:
        player = esper.get_component(cmp.Player)[0][0]
        action = None
        if self.keymap and not esper.has_component(player, cmp.Moving):
            if event.sym == tcod.event.KeySym.ESCAPE:
                raise SystemExit()
            func, args = self.action_map[event.sym]
            action = func(*args)

        return action
