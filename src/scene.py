from dataclasses import dataclass
from enum import StrEnum

import esper
import tcod

import components as cmp
import display
import processors
import board


# scene idea taken from
# https://github.com/toptea/roguelike_tutorial/blob/master/src/main.py#L180


class State(StrEnum):
    GAME = "game"
    MENU = "menu"


class Scene:
    manager = None


class MainMenu(Scene):
    def setup(self, context, console):

        render_proc = processors.MenuRenderProcessor(console, context)
        esper.add_processor(render_proc, priority=6)

        input_proc = processors.MenuInputEventProcessor()
        esper.add_processor(input_proc, priority=5)


class Game(Scene):
    def setup(self, context, console):
        visible_cmp = cmp.Visible(glyph=display.Glyph.PLAYER, color=display.Color.GREEN)
        position_cmp = cmp.Position(x=1, y=1)
        actor = cmp.Actor(hp=10, name="player")
        esper.create_entity(
            cmp.Player(), position_cmp, visible_cmp, cmp.Blocking(), actor
        )
        esper.add_processor(processors.InputEventProcessor(), priority=5)
        esper.add_processor(processors.NPCProcessor(), priority=4)
        esper.add_processor(processors.DamageProcessor(), priority=3)

        game_board = board.Board()
        render_proc = processors.RenderProcessor(console, context, game_board)
        esper.add_processor(render_proc, priority=6)
        esper.add_processor(processors.MovementProcessor(game_board))
        board.generate_dungeon(game_board)


@dataclass
class Manager:
    """Coordinates moving from Menus, game, etc"""

    scene = {
        State.MENU: MainMenu(),
        State.GAME: Game(),
    }
    current_scene = scene[State.MENU]

    @classmethod
    def change_scene(cls, state: State):
        # TODO: state machine, error handling
        cls.current_scene = cls.scene[state]
        esper.switch_world(state)
