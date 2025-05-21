import random
import time

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
    white_out = lambda _: (1, display.Color.WHITE, display.Color.WHITE)
    cell_rgbs = [list(map(white_out, row)) for row in location.BOARD.cells]

    startx, endx = (display.PANEL_WIDTH, display.R_PANEL_START)
    starty, endy = (0, display.BOARD_HEIGHT)

    console.rgb[startx:endx, starty:endy] = cell_rgbs
    context.present(console)
    esper.dispatch_event("redraw")


def flash_pos(context, console, position, color: display.Color):
    """change fg color of a position"""
    esper.dispatch_event("redraw")
    cell = location.BOARD.cells[position.x][position.y]
    glyph, _, bg = location.BOARD.as_rgb(cell)
    in_fov = location.get_fov()
    if in_fov[position.x][position.y]:
        bg = display.Color.CANDLE
    cell = (glyph, color, bg)
    console.rgb[display.PANEL_WIDTH + position.x, position.y] = cell
    context.present(console)
    time.sleep(0.05)  # display long enough to be seen


def redraw():
    scene.oneshot(processors.BoardRender)


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

    location.BOARD = location.Board()

    scene.main_menu_phase(context, console)
    scene.level_phase(context, console)
    scene.targeting_phase(context, console)
    scene.inventory_phase(context, console)
    scene.to_phase(scene.Phase.menu)
    location.generate_dungeon(location.BOARD)

    starting_spells = [
        create.firebolt_spell,
        create.blink_spell,
        create.bleed_spell,
    ]

    spells = random.sample(starting_spells, 2)
    for spell in spells:
        spell()

    create.main_menu_opts()

    flash_callback = lambda: flash(context, console)
    esper.set_handler("redraw", redraw)
    esper.set_handler("flash", flash_callback)
    flash_pos_callback = lambda x, y: flash_pos(context, console, x, y)
    esper.set_handler("flash_pos", flash_pos_callback)

    while True:
        esper.process()


if __name__ == "__main__":
    main()
