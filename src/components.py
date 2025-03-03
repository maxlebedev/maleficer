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
    glyph: str
    color: display.RGB
    # TODO: not tacking bg color yet.
    # I don't intend bg color to be a property of the glyph


@component
class Blocking:
    """Can't be moved through"""
    pass


@component
class Cell:  # floor, wall, door, etc
    pass
