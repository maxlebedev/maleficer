# import esper
import tcod
import input_handlers

FLAGS = tcod.context.SDL_WINDOW_RESIZABLE | tcod.context.SDL_WINDOW_FULLSCREEN

BOARD_WIDTH = 1920
BOARD_HEIGHT = 1080
# TODO: actually a square board leaving space for panes on the left and right would be better

def main() -> None:

    tile_atlas = "assets/dejavu10x10_gs_tc.png"
    tileset = tcod.tileset.load_tilesheet(tile_atlas, 32, 8, tcod.tileset.CHARMAP_TCOD)
    playerx = 1
    playery = 1
    keymap_path = "keymap.yaml"
    keymap = input_handlers.load_keymap(keymap_path)
    print(keymap)

    with tcod.context.new(
        width=BOARD_WIDTH,
        height=BOARD_HEIGHT,
        tileset=tileset,
        sdl_window_flags=FLAGS,
        title="Maleficer",
        vsync=True,
    ) as context:
        root_console = context.new_console(order="F")
        # this is a lot to draw every loop. if the map does any "scrolling" we'll have to redraw it all
        # TODO: see if there is a bulk print or something
        for w in range(BOARD_WIDTH):
            for h in range(BOARD_HEIGHT):
                root_console.print(x=w, y=h, string=".")
        root_console.print(x=71, y=47, string="?")
        while True:
            root_console.print(x=playerx, y=playery, string="@")

            context.present(root_console) # , integer_scaling=True
            for event in tcod.event.wait():
                # ugly elif
                if event.type == "QUIT":
                    raise SystemExit()
                elif isinstance(event, tcod.event.KeyDown):
                    root_console.print(x=playerx, y=playery, string=".")
                    if event.sym == keymap[input_handlers.Action.MOVE_DOWN]:
                        playery += 1
                    elif event.sym == keymap[input_handlers.Action.MOVE_LEFT]:
                        playerx -= 1
                    elif event.sym == keymap[input_handlers.Action.MOVE_UP]:
                        playery -= 1
                    elif event.sym == keymap[input_handlers.Action.MOVE_RIGHT]:
                        playerx += 1
                    elif event.sym == tcod.event.KeySym.ESCAPE:
                        raise SystemExit()





if __name__ == "__main__":
    main()
