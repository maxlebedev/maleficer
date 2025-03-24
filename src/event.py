import collections
import textwrap
from dataclasses import dataclass
import enum
import esper

import display
import processors as procs

# an event is somethig that happens
# an action is somthing someone did
# event conflicts with input events, and they do overlap
# am I okay with calling something an action if it doesn't have a sentient origin?


class Log:
    messages: list = []

    @classmethod
    def append(cls, text: str):
        for line in reversed(textwrap.wrap(text, display.PANEL_WIDTH - 2)):
            cls.messages.append(line.upper())

        cls.messages = cls.messages[-display.PANEL_HEIGHT - 2 :]


# global queues that help one processor delegate an action to another
class Queues:
    movement = collections.deque()
    damage = collections.deque()


@dataclass
class Damage:
    source: int
    target: int
    amount: int


@dataclass
class Movement:
    source: int
    x: int
    y: int


"""
consider this turn model:
    we have a gamestate enum
    there are functions that form a state machine over the enum
    the processors are assigned to specific gamestates, and don't run outside of those
    the proc consults GameState.proc_in_turn, and exits early if not

This also means we don't need a target event

"""

class GameState:
    # Note these GameState are unrelated to scenes
    class Group(enum.Enum):
        player = enum.auto()
        render = enum.auto()
        enemy = enum.auto()
        target = enum.auto()
        menu = enum.auto()

    turn_procs: dict
    current: Group

    @classmethod
    def set_current(cls, group: Group):
        # TODO: sate machine checks
        cls.current = group

    @classmethod
    def to_player(cls):
        cls.set_current(cls.Group.player)

    @classmethod
    def to_menu(cls):
        cls.set_current(cls.Group.menu)

    @classmethod
    def to_enemy(cls):
        cls.set_current(cls.Group.enemy)

    @classmethod
    def setup(cls):
        cls.turn_procs = {
            cls.Group.player: {procs.GameInputEventProcessor,
                               procs.RenderProcessor,
                               procs.MovementProcessor,
                               },
            cls.Group.enemy: {procs.NPCProcessor},
            # TODO: actually render happens elsewhere
            cls.Group.menu: {procs.MenuInputEventProcessor, procs.MenuRenderProcessor},
        }
        cls.current = cls.Group.player

    @classmethod
    def proc_in_turn(cls, proc: esper.Processor) -> bool:
        return type(proc) in cls.turn_procs[cls.current]

