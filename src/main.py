from typing import Tuple, Optional

import esper
import tcod
from tcod import libtcodpy

from actions import MovementAction
import components as cmp
import input_handlers
import processors
import actions

FLAGS = tcod.context.SDL_WINDOW_RESIZABLE | tcod.context.SDL_WINDOW_FULLSCREEN

BOARD_WIDTH = 1920
BOARD_HEIGHT = 1080
# TODO: actually a square board leaving space for panes on the left and right would be better
KEYMAP = None
# 840

def get_player_pos():
    for _, (_, pos) in esper.get_components(cmp.Player, cmp.Position):
        return (pos.x, pos.y)
    return (0,0)

def get_player():
    for player, (_) in esper.get_component(cmp.Player):
        return player
    return 0

class EventHandler(tcod.event.EventDispatch[actions.Action]):
    def ev_quit(self, event: tcod.event.Quit):
        raise SystemExit()

    def ev_keydown(self,  event: tcod.event.KeyDown) -> Optional[actions.Action]:
        player = get_player()
        action = None
        if KEYMAP and not esper.has_component(player, cmp.Movement):
            if event.sym == KEYMAP[input_handlers.Action.MOVE_DOWN]:
                action = actions.MovementAction(dx=0, dy=1)
            elif event.sym == KEYMAP[input_handlers.Action.MOVE_LEFT]:
                action = actions.MovementAction(dx=-1, dy=0)
            elif event.sym == KEYMAP[input_handlers.Action.MOVE_UP]:
                action = actions.MovementAction(dx=0, dy=-1)
            elif event.sym == KEYMAP[input_handlers.Action.MOVE_RIGHT]:
                action = actions.MovementAction(dx=1, dy=0)
            elif event.sym == tcod.event.KeySym.ESCAPE:
                raise SystemExit()
        return action

def as_color(text, fg: Tuple[int, int, int]=(255,255,255), bg: Tuple[int, int, int]=(0,0,0)) -> str:
    """Return the control codes to change the foreground and background colors."""
    pre = "%c%c%c%c%c%c%c%c" % (libtcodpy.COLCTRL_FORE_RGB, *fg, libtcodpy.COLCTRL_BACK_RGB, *bg)
    return f"{pre}{text}{libtcodpy.COLCTRL_STOP:c}"

def main() -> None:
    global KEYMAP

    tile_atlas = "assets/dejavu10x10_gs_tc.png"
    tileset = tcod.tileset.load_tilesheet(tile_atlas, 32, 8, tcod.tileset.CHARMAP_TCOD)
    keymap_path = "keymap.yaml"
    KEYMAP = input_handlers.load_keymap(keymap_path)

    player = esper.create_entity(cmp.Player(), cmp.Position(x=1, y=1))
    esper.add_processor(processors.MovementProcessor())
    event_handler = EventHandler()

    board_offset = 50

    context_params = {
        "width": BOARD_WIDTH,
        "height": BOARD_HEIGHT,
        "tileset": tileset,
        "sdl_window_flags": FLAGS,
        "title": "Maleficer",
        "vsync": True,
    }

    with tcod.context.new(**context_params) as context:
        root_console = context.new_console(order="F")
        # this is a lot to draw every loop. if the map does any "scrolling" we'll have to redraw it all
        # TODO: see if there is a bulk print or something
        for w in range(BOARD_WIDTH):
            for h in range(BOARD_HEIGHT):
                root_console.print(x=w+board_offset, y=h, string=".")
        root_console.print(x=71, y=47, string="?")
        root_console.draw_frame(x=0, y=0, width=board_offset, height=108, decoration="╔═╗║ ║╚═╝")
        root_console.draw_frame(x=board_offset+BOARD_WIDTH, y=0, width=board_offset, height=108, decoration="╔═╗║ ║╚═╝")
        while True:
            x, y = get_player_pos()
            pc = as_color("@", fg=(0,255,0))
            root_console.print(x=x, y=y, string=pc)

            context.present(root_console) # , integer_scaling=True
            for event in tcod.event.wait():
                action = event_handler.dispatch(event)
                if action and isinstance(action, actions.MovementAction):
                    x, y = get_player_pos()
                    # dumb hack to not have to re-render the whole screen. gotta replace
                    chr = as_color(".")
                    root_console.print(x=x, y=y, string=chr)
                    esper.add_component(player, cmp.Movement(x=action.dx, y=action.dy))

            esper.process()

if __name__ == "__main__":
    main()
