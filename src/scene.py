from dataclasses import dataclass
from enum import StrEnum

import esper

import components as cmp
import display
import processors

# taken from https://github.com/toptea/roguelike_tutorial/blob/master/src/main.py#L180


class State(StrEnum):
    GAME = "game"
    MENU = "menu"


class Scene:
    manager = None

    def update(self):
        raise NotImplementedError


class MainMenu(Scene):
    def setup(self):
        pass


class Game(Scene):
    def setup(self):
        visible_cmp = cmp.Visible(glyph=display.Glyph.PLAYER, color=display.Color.GREEN)
        position_cmp = cmp.Position(x=1, y=1)
        actor = cmp.Actor(hp=10, name="player")
        esper.create_entity(
            cmp.Player(), position_cmp, visible_cmp, cmp.Blocking(), actor
        )
        esper.add_processor(processors.InputEventProcessor(), priority=5)
        esper.add_processor(processors.NPCProcessor(), priority=4)
        esper.add_processor(processors.DamageProcessor(), priority=3)


@dataclass
class Manager:
    """Coordinates moving from Menus, game, etc"""

    scene = {
        State.MENU: MainMenu(),
        State.GAME: Game(),
    }
    current_scene = scene[State.MENU]

    def change_scene(self, state: State):
        # TODO: state machine, error handling
        self.current_scene = self.scene[state]
        esper.switch_world(state)
