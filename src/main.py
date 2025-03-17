from enum import IntEnum, StrEnum

import esper
import tcod

import board
import display
import processors
import input
import scene

FLAGS = tcod.context.SDL_WINDOW_RESIZABLE  # | tcod.context.SDL_WINDOW_FULLSCREEN


def load_tileset(atlas_path: str, width: int, height: int) -> tcod.tileset.Tileset:
    tileset = tcod.tileset.load_tilesheet(atlas_path, width, height, None)
    idx_to_point = lambda x, y: (x % y, x // y)
    for letter, val in display.letter_map.items():
        xx, yy = idx_to_point(val, width)
        tileset.remap(ord(letter), xx, yy)
    codepath = 91
    glyph_map = {}
    for glyph in display.Glyph:
        xx, yy = idx_to_point(glyph.value, width)
        tileset.remap(codepath, xx, yy)
        glyph_map[glyph.name] = codepath
        codepath += 1
    display.Glyph = IntEnum("Glyph", [(key, value) for key, value in glyph_map.items()])
    return tileset


def main() -> None:
    tile_atlas = "assets/monochrome-transparent_packed.png"
    tileset = load_tileset(tile_atlas, 49, 22)

    manager = scene.Manager()

    manager.change_scene(scene.State.GAME)
    esper.delete_world("default")

    manager.current_scene.setup()

    # esper.set_handler("target", input.Target.perform)

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
