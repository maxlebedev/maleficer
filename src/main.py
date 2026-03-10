from functools import partial

import esper
import tcod

import components as cmp
import display
import location
import phase


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

    game_meta = cmp.GameMeta(location.Board(), context, console)
    esper.create_entity(game_meta)

    position_cmp = cmp.Position(x=0, y=0)
    esper.create_entity(cmp.Crosshair(), position_cmp)

    phase.setup(context, console)
    phase.change_to(phase.Ontology.main_menu)

    while True:
        esper.process()


if __name__ == "__main__":
    main()
