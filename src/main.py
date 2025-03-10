import esper
import tcod

import board
import components as cmp
import display
import input
import processors
from enum import IntEnum

FLAGS = tcod.context.SDL_WINDOW_RESIZABLE  # | tcod.context.SDL_WINDOW_FULLSCREEN

def load_custom_tileset(atlas_path: str, x: int, y: int) -> tcod.tileset.Tileset:
    tileset = tcod.tileset.load_tilesheet(atlas_path, x, y, None)
    for letter, val in display.letter_map.items():
        yy = val // x
        xx = val % x
        tileset.remap(ord(letter), xx, yy)
    codepath = 91
    glyph_map = {}
    for glyph in display.Glyph:
        yy = glyph.value // x
        xx = glyph.value % x
        tileset.remap(codepath, xx, yy)
        glyph_map[glyph.name] = codepath
        codepath += 1
    display.Glyph = IntEnum('Glyph', [(key, value) for key, value in glyph_map.items()])
    return tileset



def main() -> None:
    tile_atlas = "assets/monochrome-transparent_packed.png"
    tileset = load_custom_tileset(tile_atlas, 49, 22)

    visible_cmp = cmp.Visible(glyph=display.Glyph.PLAYER, color=display.GREEN)
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
