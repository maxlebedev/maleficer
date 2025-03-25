import collections
import textwrap
from dataclasses import dataclass

import display

# an event is somethig that happens
# an action is somthing someone did
# event conflicts with input events, and they do overlap
# am I okay with calling something an action if it doesn't have a sentient origin?


class Log:
    """Messages to be displayed in in-game log"""
    messages: list = []

    @classmethod
    def append(cls, text: str):
        for line in reversed(textwrap.wrap(text, display.PANEL_WIDTH - 2)):
            cls.messages.append(line.upper())

        cls.messages = cls.messages[-display.PANEL_HEIGHT - 2 :]


class Queues:
    """global queues that help one processor delegate an action to another"""
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
