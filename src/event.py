import collections
from dataclasses import dataclass

# an event is somethig that happens
# an action is somthing someone did
# event conflicts with input events, and they do overlap
# am I okay with calling something an action if it doesn't have a sentient origin?


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
