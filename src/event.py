import collections
import re
from dataclasses import dataclass

import esper
import tcod

import components as cmp
import display

# an event is somethig that happens
# an action is somthing someone did
# event conflicts with input events, and they do overlap
# am I okay with calling something an action if it doesn't have a sentient origin?

RE_COLOR_CODES = re.compile(
    rf"{tcod.libtcodpy.COLCTRL_1:c}"
    rf"|{tcod.libtcodpy.COLCTRL_2:c}"
    rf"|{tcod.libtcodpy.COLCTRL_3:c}"
    rf"|{tcod.libtcodpy.COLCTRL_4:c}"
    rf"|{tcod.libtcodpy.COLCTRL_5:c}"
    rf"|{tcod.libtcodpy.COLCTRL_FORE_RGB:c}..."
    rf"|{tcod.libtcodpy.COLCTRL_BACK_RGB:c}..."
    rf"|{tcod.libtcodpy.COLCTRL_STOP:c}",
    flags=re.DOTALL,
)


class Log:
    """Messages to be displayed in in-game log"""

    messages: list = []
    max_len = display.PANEL_IHEIGHT
    curr_len = 0

    @classmethod
    def color_fmt(cls, entity: int):
        """take a string, and an entity, recolor string with entity fg"""
        message = esper.component_for_entity(entity, cmp.Onymous).name
        vis = esper.component_for_entity(entity, cmp.Visible)
        fg = vis.color
        return display.colored_text(message, fg)

    @classmethod
    def append(cls, text: str):
        clean_text = RE_COLOR_CODES.sub(repl="", string=text)
        print(clean_text)

        ghr = tcod.console.get_height_rect
        lines = ghr(width=display.PANEL_IWIDTH, string=clean_text)

        cls.curr_len += lines

        cls.messages.append((text, lines))
        while cls.curr_len > cls.max_len:
            cls.curr_len -= cls.messages[0][1]
            cls.messages = cls.messages[1:]


class Queues:
    """global queues that help one processor delegate an action to another"""

    movement = collections.deque()
    damage = collections.deque()
    tick = collections.deque()
    death = collections.deque()


class Event:
    _queue: collections.deque

    def __post_init__(self):
        self._queue.append(self)


@dataclass
class Damage(Event):
    _queue = Queues.damage
    source: dict
    target: int
    amount: int


@dataclass
class Movement(Event):
    _queue = Queues.movement
    source: int
    x: int
    y: int
    relative: bool = False


@dataclass
class Tick(Event):
    """A tick event is used to explicity track turns, for upkeeps"""

    _queue = Queues.tick


@dataclass
class Death(Event):
    _queue = Queues.death
    entity: int

    def __post_init__(self):
        if self.entity not in [e.entity for e in self._queue]:
            self._queue.append(self)


def trigger_all_callbacks(entity, trigger_cmp):
    if trigger := esper.try_component(entity, trigger_cmp):
        for func in trigger.callbacks:
            if not esper.entity_exists(entity):
                return
            func(entity)
            # TODO: the main callback that needs a ref to source is lob_bomb
            # TypeError

    # I don't remember why these are here.
    # item use and spells have their own. so perhaps enemy/death
    if esper.entity_exists(entity) and esper.has_component(entity, cmp.Target):
        esper.remove_component(entity, cmp.Target)
