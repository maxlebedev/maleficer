import esper
import tcod

import display
import location
import scene
import create

FLAGS = tcod.context.SDL_WINDOW_RESIZABLE  # | tcod.context.SDL_WINDOW_FULLSCREEN


def main() -> None:
    tile_atlas = "assets/monochrome-transparent_packed.png"
    tileset = display.load_tileset(tile_atlas, display.TS_WIDTH, display.TS_HEIGHT)
    display.Glyph = display.remap_glyphs()

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

    create.player()

    game_board = location.Board()

    create.main_menu(context, console)
    create.level(context, console, game_board)
    create.targeting(context, console, game_board)
    scene.to_phase(scene.Phase.menu)

    create.inventory()

    while True:
        esper.process()


if __name__ == "__main__":
    main()
