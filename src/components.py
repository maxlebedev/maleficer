from collections.abc import Callable
from dataclasses import dataclass as component
from typing import TypeVar

import display
import typ

T = TypeVar("T")


@component
class Player:
    pass


@component
class Position:
    x: int
    y: int

    def __iter__(self):
        return iter([self.x, self.y])

    def lookup_in(self, matrix: list[list[T]]) -> T:
        # IDK if I'm keeping this yet
        return matrix[self.x][self.y]

    @property
    def as_tuple(self):
        return (self.x, self.y)


@component
class Moving:
    x: int
    y: int


@component
class Visible:
    glyph: int
    color: typ.RGB = display.Color.WHITE
    bg_color: typ.RGB = display.Color.BLACK
    # bg_color mostly represents explored state, rather than a property of the entity


@component
class Transparent:
    """does not block light"""


@component
class Blocking:
    """Can't be moved through"""


@component
class Cell:  # floor, wall, door, etc
    pass


@component
class Enemy:
    pass


@component
class Wander:
    """Walks around randomly"""


@component
class Melee:
    """Walks towards player"""

    radius: int


@component
class Ranged:
    """Damages player if in LOS"""

    radius: int


@component
class Onymous:
    name: str
    # death string?


@component
class Health:  # Destroyable, harmable?
    max: int
    armor: int = 0

    def __post_init__(self):
        self.current = self.max


@component
class Crosshair:
    """used for target selection"""


@component
class EffectArea:
    radius: int = 0


@component
class Collectable:
    """can be added to inventory"""


@component
class InInventory:
    pass


@component
class Spell:
    target_range: int


@component
class Cooldown:
    turns: int

    def __post_init__(self):
        self.turns += 1


@component
class Target:
    target: int  # Not loving the stutter


@component
class MenuSelection:
    item: int = 0


@component
class MenuItem:
    order: int


@component
class MainMenu:
    """Indicates an element of the main menu"""

    pass


@component
class DamageEffect:
    """a spell (or w.e) deals damage"""

    source: int
    amount: int


@component
class MoveEffect:
    """a spell (or w.e) moves a target"""

    # target is chosen at spell creation time,
    # so this won't work for arbitrary enemies
    target: int


@component
class HealEffect:
    amount: int


@component
class BleedEffect:
    value: int


@component
class State:
    """all of the conditions that an entity have"""

    map: dict[typ.Condition, int]  # maybe some conditions are additive?


@component
class OnStep:
    """activates an effect when walked on"""


@component
class OnDeath:
    """activates an effect when entity dies"""


@component
class Flying:
    """not affected by OnStep components"""


@component
class Targeting:
    """entity invoking target phase"""


@component
class Learnable:
    """use to learn spell"""

    spell: int


@component
class Known:
    """spell is castable"""

    slot: int


@component
class Trigger:
    callbacks: list[Callable]


@component
class DeathTrigger(Trigger):
    pass


@component
class UseTrigger(Trigger):
    """item use, spell use, menu selection"""

    pass


@component
class StepTrigger(Trigger):
    pass


@component
class EnemyTrigger(Trigger):
    pass
