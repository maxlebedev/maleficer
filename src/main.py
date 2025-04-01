import esper
import tcod

import components as cmp
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

    visible_cmp = cmp.Visible(glyph=display.Glyph.PLAYER, color=display.Color.GREEN)
    position_cmp = cmp.Position(x=1, y=1)
    actor = cmp.Actor(max_hp=10, name="player")
    esper.create_entity(cmp.Player(), position_cmp, visible_cmp, cmp.Blocking(), actor)

    game_board = location.Board()

    scene.main_menu_setup(context, console)
    scene.level_setup(context, console, game_board)
    scene.targeting_setup(context, console, game_board)
    scene.to_phase(scene.Phase.menu)

    while True:
        esper.process()


if __name__ == "__main__":
    main()
