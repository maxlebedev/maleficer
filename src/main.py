import esper
import tcod

import board
import components as cmp
import display
import input
import processors

FLAGS = tcod.context.SDL_WINDOW_RESIZABLE  # | tcod.context.SDL_WINDOW_FULLSCREEN


def load_custom_tileset(atlas_path: str, x: int, y: int) -> tcod.tileset.Tileset:
    tileset = tcod.tileset.load_tilesheet(atlas_path, x, y, None)
    codepath = 0
    for yy in range(0, y):
        for xx in range(0, x):
            tileset.remap(codepath, xx, yy)
            codepath += 1
    return tileset


def main() -> None:
    # tile_atlas = "assets/dejavu10x10_gs_tc.png"
    # tileset = tcod.tileset.load_tilesheet(tile_atlas, 32, 8, tcod.tileset.CHARMAP_TCOD)
    # display.TILE_SIZE = 16
    tile_atlas = "assets/monochrome-transparent_packed.png"
    tileset = load_custom_tileset(tile_atlas, 49, 22)

    visible_cmp = cmp.Visible(
        glyph=display.Glyph.PLAYER, color=display.GREEN, bg_color=display.DGREY
    )
    position_cmp = cmp.Position(x=1, y=1)
    esper.create_entity(cmp.Player(), position_cmp, visible_cmp, cmp.Blocking())
    event_handler = input.EventHandler()
    esper.add_processor(processors.EventProcessor(event_handler), priority=5)
    esper.add_processor(processors.NPCProcessor(), priority=4)

    context_params = {
        "width": display.CONSOLE_WIDTH,
        "height": display.CONSOLE_HEIGHT,
        "tileset": tileset,
        "sdl_window_flags": FLAGS,
        "title": "Maleficer",
        "vsync": True,
    }

    # TODO: would it be better to make the side panels their own consoles?
    # the way to do this is to blit() sub-consoles onto a root console
    # nice to have a clean coord set for each sub-console but that's kind of it
    with tcod.context.new(**context_params) as context:
        console = context.new_console(order="F")
        game_board = board.Board()
        render_proc = processors.RenderProcessor(console, context, game_board)
        esper.add_processor(render_proc, priority=6)
        esper.add_processor(processors.MovementProcessor(game_board))
        board.generate_dungeon(game_board)

        while True:
            esper.process()


if __name__ == "__main__":
    main()
