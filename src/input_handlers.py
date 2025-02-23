import yaml
import tcod
from enum import Enum


class Action(Enum):
    MOVE_UP = 1
    MOVE_DOWN = 2
    MOVE_LEFT = 3
    MOVE_RIGHT = 4

def load_keymap(keymap_json_path):
    with open(keymap_json_path, 'r') as file:
        keymap_data = yaml.safe_load(file)

    key_action_mapping = {}

    for action_name, key_name in keymap_data.items():
        try:
            # assuming yaml fileuses KeySym format. brittle
            key_sym = getattr(tcod.event.KeySym, key_name, None)
            if key_sym is None:
                raise ValueError(f"Invalid key symbol: {key_name}")

            action = Action[action_name]
            key_action_mapping[action] = key_sym

        except KeyError:
            print(f"Warning: Action {action_name} not found in Action Enum.")
        except ValueError as ve:
            print(f"Error: {ve}")

    return key_action_mapping
