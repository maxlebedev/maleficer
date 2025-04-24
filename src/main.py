import esper
import tcod

import create
import display
import location
import processors
import scene

FLAGS = tcod.context.SDL_WINDOW_RESIZABLE  # | tcod.context.SDL_WINDOW_FULLSCREEN


def flash(context, console):
    """flashes the screen, for use on errors"""
    console.clear()
    foo = lambda _: (1, display.Color.WHITE, display.Color.WHITE)
    cell_rgbs = [list(map(foo, row)) for row in location.BOARD.cells]

    startx, endx = (display.PANEL_WIDTH, display.R_PANEL_START)
    starty, endy = (0, display.BOARD_HEIGHT)

    console.rgb[startx:endx, starty:endy] = cell_rgbs
    context.present(console)  # , integer_scaling=True
    scene.oneshot(processors.BoardRenderProcessor)


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

    location.BOARD = location.Board()

    scene.main_menu_phase(context, console)
    scene.level_phase(context, console)
    scene.targeting_phase(context, console)
    scene.inventory_phase(context, console)
    scene.to_phase(scene.Phase.menu)
    location.generate_dungeon(location.BOARD)

    scene.inventory_setup()
    create.inventory_map()
    create.damage_spell()
    create.tp_spell()

    while True:
        esper.process()


if __name__ == "__main__":
    main()
