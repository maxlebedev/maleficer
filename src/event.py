import collections
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

    @classmethod
    def append(cls, text: str):
        print(text)
        for line in textwrap.wrap(text, display.PANEL_WIDTH - 2):
            cls.messages.append(line.upper())

        cls.messages = cls.messages[-display.PANEL_HEIGHT - 3 :]


class Queues:
    """global queues that help one processor delegate an action to another"""

    movement = collections.deque()
    damage = collections.deque()
    tick = collections.deque()


class Event:
    _queue: collections.deque

    def __post_init__(self):
        self._queue.append(self)


@dataclass
class Damage(Event):
    _queue = Queues.damage
    source: int
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


def effects_to_events(source: int):
    """take an entity read effects off the entity and apply them to crosshair if needed"""
    # do I need to build an entity cache?

    # TODO: are we guarenteed to have a target every time?
    target = esper.component_for_entity(source, cmp.Target).target
    if dmg_effect := esper.try_component(source, cmp.DamageEffect):
        if esper.has_component(target, cmp.Cell):
            pos = esper.component_for_entity(target, cmp.Position)
            for ent in location.BOARD.entities[pos.x][pos.y]:
                if esper.has_component(ent, cmp.Actor):
                    Damage(dmg_effect.source, ent, dmg_effect.amount)
        else:
            Damage(dmg_effect.source, target, dmg_effect.amount)

    player = ecs.Query(cmp.Player, cmp.Position).first()
    player_pos = ecs.cmps[player][cmp.Position]
    if move_effect := esper.try_component(source, cmp.MoveEffect):
        pos = ecs.Query(cmp.Crosshair, cmp.Position).cmp(cmp.Position)
        x = pos.x - player_pos.x
        y = pos.y - player_pos.y
        Movement(move_effect.target, x, y)

    if heal_effect := esper.try_component(source, cmp.HealEffect):
        Damage(source, player, -1 * heal_effect.amount)

    if cd_effect := esper.try_component(source, cmp.Cooldown):
        condition.grant(source, typ.Condition.Cooldown, cd_effect.turns)

    # note that removing Target is bad if persistent entity with static target
    esper.remove_component(source, cmp.Target)
