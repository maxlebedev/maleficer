from enum import Enum

import tcod
import yaml
import esper
import components as cmp

"""
Clarifying related terms

Keybind: the physical key (from yaml file)
Input: the input option
Actions: a player has chosen an in-game option

We map Keybinds to Inputs via keymap
"""


class Input(Enum):
    MOVE_UP = 1
    MOVE_DOWN = 2
    MOVE_LEFT = 3
    MOVE_RIGHT = 4
    ESC = 5
    ONE = 6
    SELECT = 7


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


def target(): # TODO: takes a board?
    print("in target")
    _, (_, pos) = esper.get_components(cmp.Player, cmp.Position)[0]
    fov_source = (pos.x, pos.y)
    done = False
    while not done:
        for input_event in tcod.event.wait():
            # if we ever have other events we care abt, we can dispatch by type
            if not isinstance(input_event, tcod.event.KeyDown):
                continue
            if input_event.sym == KEYMAP[Input.MOVE_DOWN]:
                fov_source = (fov_source[0],fov_source[1]+1)
                print("Down")
            elif input_event.sym == KEYMAP[Input.MOVE_UP]:
                fov_source = (fov_source[0],fov_source[1]-1)
                print("UP")
            elif input_event.sym == KEYMAP[Input.ESC]:
                done = True
