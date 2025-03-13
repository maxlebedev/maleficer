import collections
from dataclasses import dataclass

# an event is somethig that happens
# an action is somthing someone did
# event conflicts with input events, and they do overlap
# am I okay with calling something an action if it doesn't have a sentient origin?

class Log:
    messages: list = []

    @classmethod
    def append(cls, text: str):
        trimmed_text = text[:display.PANEL_WIDTH-2].upper()
        # TODO: break into two lines instead maybe
        cls.messages.append(trimmed_text)
        cls.messages = cls.messages[-display.PANEL_HEIGHT-2:]


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
