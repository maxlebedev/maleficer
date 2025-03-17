from enum import IntEnum, StrEnum

import esper
import tcod

import display
import scene


FLAGS = tcod.context.SDL_WINDOW_RESIZABLE  # | tcod.context.SDL_WINDOW_FULLSCREEN


def main() -> None:
    scene.Manager.change_scene(scene.State.MENU)
    esper.delete_world("default")

    tile_atlas = "assets/monochrome-transparent_packed.png"
    tileset = display.load_tileset(tile_atlas, 49, 22)

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

    for state in scene.State:
        scene.Manager.change_scene(state)
        scene.Manager.current_scene.setup(context, console)
        esper.set_handler("change_scene", scene.Manager.change_scene)

    while True:
        esper.process()


if __name__ == "__main__":
    main()
