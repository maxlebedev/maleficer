from dataclasses import dataclass as component

import display


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
    color: display.RGB = display.WHITE
    bg_color: display.RGB = display.BLACK
    # bg_color mostly represents explored state. Grey by default, black when in view
    # or maybe grey as my light source


@component
class Transparent:
    pass


@component
class Blocking:
    """Can't be moved through"""

    pass


@component
class Cell:  # floor, wall, door, etc
    pass
