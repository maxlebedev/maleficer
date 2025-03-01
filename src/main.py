from typing import Tuple

import esper
import tcod
from tcod import libtcodpy

import actions
import components as cmp
import processors
import engine
import display

FLAGS = tcod.context.SDL_WINDOW_RESIZABLE | tcod.context.SDL_WINDOW_FULLSCREEN

# TODO: actually a square board leaving space for panes on the left and right would be better
RGB = Tuple[int, int, int]


def get_player_pos():
    for _, (_, pos) in esper.get_components(cmp.Player, cmp.Position):
        return (pos.x, pos.y)
    return (0, 0)


def as_color(text, fg: RGB = (255, 255, 255), bg: RGB = (0, 0, 0)) -> str:
    """Return the control codes to change the foreground and background colors."""
    fore_rgb = libtcodpy.COLCTRL_FORE_RGB
    back_rgb = libtcodpy.COLCTRL_BACK_RGB

    pre = "%c%c%c%c%c%c%c%c" % (fore_rgb, *fg, back_rgb, *bg)
    return f"{pre}{text}{libtcodpy.COLCTRL_STOP:c}"


def main() -> None:

    tile_atlas = "assets/dejavu10x10_gs_tc.png"
    tileset = tcod.tileset.load_tilesheet(tile_atlas, 32, 8, tcod.tileset.CHARMAP_TCOD)

    visible_cmp = cmp.Visible(glyph="@", color=(0, 255, 0))
    player = esper.create_entity(
        cmp.Player(), cmp.Position(x=1, y=1), visible_cmp
    )
    esper.add_processor(processors.MovementProcessor())
    event_handler = engine.EventHandler()

    context_params = {
        "width": display.CONSOLE_WIDTH,
        "height": display.CONSOLE_HEIGHT,
        "tileset": tileset,
        "sdl_window_flags": FLAGS,
        "title": "Maleficer",
        "vsync": True,
    }

    with tcod.context.new(**context_params) as context:
        root_console = context.new_console(order="F")
        # this is a lot to draw every loop. if the map does any "scrolling" we'll have to redraw it all
        # TODO: see if there is a bulk print or something
        for w in range(display.BOARD_WIDTH):
            for h in range(display.BOARD_HEIGHT):
                root_console.print(x=w + display.PANEL_WIDTH, y=h, string=".")
        root_console.print(x=71, y=47, string="?")
        myengine = engine.Engine(event_handler=event_handler)
        while True:
            # root_console.clear()

            myengine.render(console=root_console, context=context)

            context.present(root_console)  # , integer_scaling=True
            for event in tcod.event.wait():
                action = event_handler.dispatch(event)
                if action and isinstance(action, actions.MovementAction):
                    x, y = get_player_pos()
                    # dumb hack to not have to re-render the whole screen. gotta replace
                    chr = as_color(".")
                    root_console.print(x=x + display.PANEL_WIDTH, y=y, string=chr)
                    esper.add_component(player, cmp.Movement(x=action.dx, y=action.dy))

            esper.process()


if __name__ == "__main__":
    main()
