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
class Actor:  # Destroyable
    name: str  # consider a Named/Onymous component?
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
    pass


@component
class MenuSelection:
    item: int = 0
    pass


@component
class MenuItem:
    order: int
