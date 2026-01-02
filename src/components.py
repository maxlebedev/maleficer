import typing
from collections.abc import Callable
from dataclasses import dataclass as component

import display
import typ

T = typing.TypeVar("T")


@component
class Player:
    perception_radius: int = 10
    sight_radius: int = 4


@component
class GameMeta:
    board: object  # location.Board
    menu_selection: int = 0
    process: None = None


@component
class MapInfo:
    mood: dict
    depth: int
    wall_glyph: int
    bwall_glyph: int


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

    @property
    def as_list(self):
        return [self.x, self.y]

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y


@component
class LastPosition:
    pos: Position


@component
class Visible:
    glyph: int
    color: typ.RGB = display.Color.WHITE
    bg_color: typ.RGB = display.Color.BLACK
    # bg_color mostly represents explored state, rather than a property of the entity


@component
class Opaque:
    """blocks light"""


@component
class Blocking:
    """Can't be moved through"""


@component
class Cell:  # floor, wall, door, etc
    pass


@component
class Wall(Cell):
    pass


@component
class Door(Cell):
    closed = True


@component
class Enemy:
    evaluate: Callable | None = None
    action: Callable | None = None
    speed: int = 1
    perception: int = 4


@component
class Wander:
    """Walks around randomly"""


@component
class Melee:
    """damages on bump"""


@component
class Ranged:
    """Damages player if in LOS"""


@component
class KnownAs:
    """this entity is known as"""

    name: str
    # death string?


@component
class Health:  # Destroyable, harmable?
    max: int

    def __post_init__(self):
        self.current = self.max


@component
class Crosshair:
    """used for target selection"""


# The difference between EffectArea and Locus is that EA is dynamic
@component
class EffectArea:
    callback: Callable  # takes pos, return list[x,y]


@component
class Locus:
    """a static set of coords for AOEs and such"""

    coords: list[typ.Coord]


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

    prev = None


@component
class StartMenu:
    """Indicates an element of the start menu"""

    import phase

    prev = phase.Ontology.main_menu


@component
class DamageEffect:
    """a spell (or w.e) deals damage"""

    source: int
    amount: int
    die_type: int | None = None

    @property
    def desc(self) -> str:
        if self.die_type:
            return f"{self.amount}d{self.die_type}"
        return str(self.amount)

    def calculate(self):
        import math_util

        if self.die_type:
            return math_util.roll(self.amount, self.die_type)
        return self.amount


@component
class MoveEffect:
    """a spell (or w.e) moves a target to crosshair"""

    # target is chosen at spell creation time,
    # so this won't work for arbitrary enemies
    target: int


@component
class PushEffect:
    """different take on forced movement"""

    source: int
    distance: int


@component
class PullEffect:
    """different take on forced movement"""

    source: int


@component
class HealEffect:
    amount: int


@component
class BleedEffect:
    value: int


@component
class StunEffect:
    value: int


@component
class AegisEffect:
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
class Attuned:
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


@component
class Aura:
    """Visual radius"""

    color: typ.RGB
    callback: Callable  # takes pos, return list[x,y]
