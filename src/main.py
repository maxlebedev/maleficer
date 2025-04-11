import esper
import tcod

import display
import location
import scene

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

    scene.player_setup()

    game_board = location.Board()

    scene.main_menu_phase(context, console)
    scene.level_phase(context, console, game_board)
    scene.targeting_phase(context, console, game_board)
    scene.inventory_phase(context, console, game_board)
    scene.to_phase(scene.Phase.menu)

    scene.inventory_setup()

    while True:
        esper.process()


if __name__ == "__main__":
    main()
