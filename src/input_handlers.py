from enum import Enum
from typing import Dict

import tcod
import yaml

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


KeyMap = Dict[tcod.event.KeySym,Input]

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
