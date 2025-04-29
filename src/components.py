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
    color: typ.RGB
    # radius/cell set/aoe formula?


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
class State:
    """all of the conditions that an entity have"""

    map: dict[typ.Condition, int]  # maybe some conditions are additive?


@component
class Trap:
    """activates an effect when walked on"""


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
