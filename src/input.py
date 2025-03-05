from enum import Enum

import tcod
import yaml

import actions

"""
Clarifying related terms

Keybind: the physical key (from yaml file)
Input: the input option
Actions: a player has chosen an in-game option

We map Keybinds to Inputs via keymap
"""


# TODO: change this name
class Input(Enum):
    MOVE_UP = 1
    MOVE_DOWN = 2
    MOVE_LEFT = 3
    MOVE_RIGHT = 4
    ESC = 5


KeyMap = dict[tcod.event.KeySym, Input]


def load_keymap(keymap_json_path):
    with open(keymap_json_path, "r") as file:
        keymap_data = yaml.safe_load(file)

    key_map = {}

    for action_name, key_name in keymap_data.items():
        try:
            # assuming yaml fileuses KeySym format. brittle
            key_sym = getattr(tcod.event.KeySym, key_name, None)
            if key_sym is None:
                raise ValueError(f"Invalid key symbol: {key_name}")

            action = Input[action_name]
            key_map[action] = key_sym

        except KeyError:
            print(f"Warning: Action {action_name} not found in Action Enum.")
        except ValueError as ve:
            print(f"Error: {ve}")

    return key_map


class EventHandler(tcod.event.EventDispatch[actions.Action]):
    def __init__(self):
        keymap_path = "keymap.yaml"
        self.keymap = load_keymap(keymap_path)
        self.action_map = {
            self.keymap[Input.MOVE_DOWN]: (actions.MovementAction, (0, 1)),
            self.keymap[Input.MOVE_LEFT]: (actions.MovementAction, (-1, 0)),
            self.keymap[Input.MOVE_UP]: (actions.MovementAction, (0, -1)),
            self.keymap[Input.MOVE_RIGHT]: (actions.MovementAction, (1, 0)),
            self.keymap[Input.ESC]: (self.ev_quit, (tcod.event.Quit,)),
        }

    def ev_quit(self, event: tcod.event.Quit):
        raise SystemExit()

    def ev_keydown(self, event: tcod.event.KeyDown) -> actions.Action | None:
        action = None
        if self.keymap and event.sym in self.action_map:
            func, args = self.action_map[event.sym]
            action = func(*args)
        return action
