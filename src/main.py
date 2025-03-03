import esper

import tcod

import components as cmp
import display
import engine
import processors
from board import Board

FLAGS = tcod.context.SDL_WINDOW_RESIZABLE | tcod.context.SDL_WINDOW_FULLSCREEN


def main() -> None:
    tile_atlas = "assets/dejavu10x10_gs_tc.png"
    tileset = tcod.tileset.load_tilesheet(tile_atlas, 32, 8, tcod.tileset.CHARMAP_TCOD)

    visible_cmp = cmp.Visible(glyph="@", color=display.GREEN)
    position_cmp = cmp.Position(x=1, y=1)
    esper.create_entity(cmp.Player(), position_cmp, visible_cmp)
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
        board = Board()
        render_proc = processors.RenderProcessor(console, context, board)
        esper.add_processor(render_proc)
        esper.add_processor(processors.MovementProcessor(board))
        board.set_cell(2, 4, glyph="0")
        esper.add_component(board.get_cell(2, 4), cmp.Blocking())

        while True:
            esper.process()


if __name__ == "__main__":
    main()
