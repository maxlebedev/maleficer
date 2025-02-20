# TODO: make libsdl2-dev a req
# import esper
import tcod

"""
export LIBGL_ALWAYS_SOFTWARE=1

MESA: error: ZINK: failed to choose pdev
glx: failed to create drisw screen
"""
FLAGS = tcod.context.SDL_WINDOW_RESIZABLE | tcod.context.SDL_WINDOW_FULLSCREEN


def main() -> None:
    screen_width = 1920  # 3840 # 720 # 80
    screen_height = 1080  # 480 # 50

    tile_atlas = "assets/dejavu10x10_gs_tc.png"
    tileset = tcod.tileset.load_tilesheet(tile_atlas, 32, 8, tcod.tileset.CHARMAP_TCOD)

    with tcod.context.new(
        width=screen_width,
        height=screen_height,
        tileset=tileset,
        sdl_window_flags=FLAGS,
        title="Maleficer",
        vsync=True,
    ) as context:
        root_console = context.new_console(order="F")
        while True:
            for w in range(screen_width):
                for h in range(screen_height):
                    root_console.print(x=w, y=h, string=".")
            root_console.print(x=1, y=1, string="@")
            root_console.print(x=71, y=47, string="?")

            context.present(root_console, integer_scaling=True)

            for event in tcod.event.wait():
                if event.type == "QUIT":
                    raise SystemExit()
                elif isinstance(event, tcod.event.KeyDown):
                    if event.sym == tcod.event.KeySym.ESCAPE:
                        raise SystemExit()


if __name__ == "__main__":
    main()
