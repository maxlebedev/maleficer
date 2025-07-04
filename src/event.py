import collections
import random
import textwrap
from dataclasses import dataclass

import esper

import components as cmp
import condition
import display
import ecs
import location
import typ

# an event is somethig that happens
# an action is somthing someone did
# event conflicts with input events, and they do overlap
# am I okay with calling something an action if it doesn't have a sentient origin?


class Log:
    """Messages to be displayed in in-game log"""

    messages: list = []
    log_len = display.PANEL_HEIGHT - 2

    @classmethod
    def append(cls, text: str):
        print(text)
        for line in textwrap.wrap(text, display.PANEL_WIDTH - 2):
            cls.messages.append(line)

        cls.messages = cls.messages[-cls.log_len :]
        esper.dispatch_event("redraw")


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


def collect_all_affected_entities(source: int, target: int) -> list[int]:
    pos = esper.component_for_entity(target, cmp.Position)
    if not esper.has_component(source, cmp.EffectArea):
        entities = [e for e in location.BOARD.entities[pos.x][pos.y]]
        return entities
    aoe = esper.component_for_entity(source, cmp.EffectArea)

    entities = []

    for x, y in location.coords_within_radius(pos, aoe.radius):
        entities += [e for e in location.BOARD.entities[x][y] if e != source]
    return entities


def trigger_all_callbacks(entity, trigger_cmp):
    if trigger := esper.try_component(entity, trigger_cmp):
        for func in trigger.callbacks:
            if not esper.entity_exists(entity):
                return
            func(entity)
            # TypeError

    # I don't remember why these are here.
    # item use and spells have their own. so perhaps enemy/death
    if esper.entity_exists(entity) and esper.has_component(entity, cmp.Target):
        esper.remove_component(entity, cmp.Target)
