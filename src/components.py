from dataclasses import dataclass as component

import display
import typ


@component
class Player:
    pass


@component
class Position:
    x: int
    y: int


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

    pass


@component
class Blocking:
    """Can't be moved through"""

    pass


@component
class Cell:  # floor, wall, door, etc
    pass


@component
class Enemy:
    pass


@component
class Wander:
    """Walks around randomly"""

    pass


@component
class Melee:
    """Walks towards player"""

    radius: int
    pass


@component
class Onymous:
    name: str


@component
class Actor:  # Destroyable, harmable?
    max_hp: int
    armor: int = 0

    def __post_init__(self):
        self.hp = self.max_hp


@component
class Crosshair:
    pass


@component
class EffectArea:
    color: typ.RGB
    # radius/cell set/aoe formula?


@component
class Collectable:
    """can be added to inventory"""

    pass


@component
class InInventory:
    pass


@component
class Spell:
    slot: int
    target_range: int
    # mana cost?
    pass


@component
class CurrentSpell:
    """the spell we are casting right now"""

    pass


@component
class MenuSelection:
    item: int = 0
    pass


@component
class MenuItem:
    order: int


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
    target: int
    amount: int


# TODO: maybe if MoveEffect, HealEffect lack a target, we go into target phase to get one?


@component
class State:
    """all of the conditions that an entity have"""

    map: dict[typ.Condition, int]
