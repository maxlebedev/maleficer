from typing import Tuple

import esper
import tcod
from tcod import libtcodpy

import actions
import components as cmp
import processors
import engine
import display
from board import Board


FLAGS = tcod.context.SDL_WINDOW_RESIZABLE | tcod.context.SDL_WINDOW_FULLSCREEN

RGB = Tuple[int, int, int]


def get_player_pos():
    for _, (_, pos) in esper.get_components(cmp.Player, cmp.Position):
        return (pos.x, pos.y)
    return (0, 0)


def as_color(text, fg: RGB = display.WHITE, bg: RGB = display.BLACK) -> str:
    """Return the control codes to change the foreground and background colors."""
    fore_rgb = libtcodpy.COLCTRL_FORE_RGB
    back_rgb = libtcodpy.COLCTRL_BACK_RGB

    pre = "%c%c%c%c%c%c%c%c" % (fore_rgb, *fg, back_rgb, *bg)
    return f"{pre}{text}{libtcodpy.COLCTRL_STOP:c}"


def main() -> None:
    tile_atlas = "assets/dejavu10x10_gs_tc.png"
    tileset = tcod.tileset.load_tilesheet(tile_atlas, 32, 8, tcod.tileset.CHARMAP_TCOD)

    visible_cmp = cmp.Visible(glyph="@", color=display.GREEN)
    position_cmp = cmp.Position(x=1, y=1)
    esper.create_entity(cmp.Player(), position_cmp, visible_cmp)
    esper.add_processor(processors.MovementProcessor())
    event_handler = engine.EventHandler()
    esper.add_processor(processors.EventProcessor(event_handler))

    context_params = {
        "width": display.CONSOLE_WIDTH,
        "height": display.CONSOLE_HEIGHT,
        "tileset": tileset,
        "sdl_window_flags": FLAGS,
        "title": "Maleficer",
        "vsync": True,
    }

    with tcod.context.new(**context_params) as context:
        console = context.new_console(order="F")
        esper.add_processor(processors.RenderProcessor(event_handler, console, context))

        board = Board()
        # this is a test, delete
        example_tile = board.get_tile(0,4)
        board.flip_tile(console, 0,4)
        pos = esper.component_for_entity(example_tile, cmp.Position)
        print(pos) # Position(x=0, y=4)

        while True:
            esper.process()


if __name__ == "__main__":
    main()
