from functools import partial

import esper
import tcod

import components as cmp
import display
import location
import phase
import processors


def flash(context, console):
    """flashes the screen, for use on errors"""
    console.clear()
    board = location.get_board()
    white_out = lambda _: (1, display.Color.WHITE, display.Color.WHITE)
    cell_rgbs = [list(map(white_out, row)) for row in board.cells]

    display.write_rgbs(console, cell_rgbs)
    context.present(console)

    esper.dispatch_event("redraw")


def redraw():
    phase.oneshot(processors.BoardRender)


def main() -> None:
    tile_atlas = "assets/monochrome-transparent_packed.png"
    tileset = display.load_tileset(tile_atlas, display.TS_WIDTH, display.TS_HEIGHT)
    display.Glyph = display.remap_glyphs()

    context_params = {
        "width": display.CONSOLE_WIDTH,
        "height": display.CONSOLE_HEIGHT,
        "tileset": tileset,
        "title": "Maleficer",
        "vsync": True,
    }

    context = tcod.context.new(**context_params)
    console = context.new_console(order="F")

    context.present = partial(context.present, keep_aspect=True)
    if context.sdl_window:
        context.sdl_window.fullscreen = tcod.context.SDL_WINDOW_FULLSCREEN_DESKTOP

    color_mood = display.Mood.shuffle()
    game_meta = cmp.GameMeta(board=location.Board(), mood=color_mood)
    esper.create_entity(game_meta)

    phase.setup(context, console)
    phase.change_to(phase.Ontology.main_menu)

    flash_callback = lambda: flash(context, console)
    esper.set_handler("redraw", redraw)
    esper.set_handler("flash", flash_callback)

    def fullscreen_toggle():
        if context.sdl_window:
            toggle = int(not context.sdl_window.fullscreen)
            context.sdl_window.fullscreen = toggle

    esper.set_handler("fullscreen_toggle", fullscreen_toggle)

    while True:
        esper.process()


if __name__ == "__main__":
    main()
