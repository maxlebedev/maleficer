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

FLAGS = tcod.context.SDL_WINDOW_RESIZABLE  # | tcod.context.SDL_WINDOW_FULLSCREEN


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
        tile_atlas = "assets/monochrome-transparent_packed.png"
        tileset = display.load_tileset(tile_atlas, 49, 22)

        visible_cmp = cmp.Visible(glyph=display.Glyph.PLAYER, color=display.Color.GREEN)
        position_cmp = cmp.Position(x=1, y=1)
        actor = cmp.Actor(hp=10, name="player")
        esper.create_entity(
            cmp.Player(), position_cmp, visible_cmp, cmp.Blocking(), actor
        )
        esper.add_processor(processors.InputEventProcessor(), priority=5)
        esper.add_processor(processors.NPCProcessor(), priority=4)
        esper.add_processor(processors.DamageProcessor(), priority=3)

        context_params = {
            "width": display.CONSOLE_WIDTH,
            "height": display.CONSOLE_HEIGHT,
            "tileset": tileset,
            "sdl_window_flags": FLAGS,
            "title": "Maleficer",
            "vsync": True,
        }

        context = tcod.context.new(**context_params)
        console = context.new_console(order="F")
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

    def change_scene(self, state: State):
        # TODO: state machine, error handling
        self.current_scene = self.scene[state]
        esper.switch_world(state)
