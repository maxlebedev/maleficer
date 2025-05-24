import enum

import tcod
import yaml

"""
Clarifying related terms

Keybind: the physical key/keysym (from yaml file)
Input: the labels for input option
Actions: functions fired from the key presses

We map Keybinds to Inputs via keymap
And then Inputs to Actions vis action_map
"""


class Input(enum.Enum):
    MOVE_UP = enum.auto()
    MOVE_DOWN = enum.auto()
    MOVE_LEFT = enum.auto()
    MOVE_RIGHT = enum.auto()
    ESC = enum.auto()
    SELECT = enum.auto()
    SPELL1 = enum.auto()
    SPELL2 = enum.auto()
    SPELL3 = enum.auto()
    SPELL4 = enum.auto()
    INVENTORY = enum.auto()
    SKIP = enum.auto()


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


KEYMAP = load_keymap("keymap.yaml")
