from typing import Tuple
from dataclasses import dataclass as component


@component
class Player:
    pass


@component
class Position:
    x: int
    y: int


@component
class Movement:
    # TODO: name could probably be better
    x: int
    y: int


@component
class Visible:
    glyph: str
    color: Tuple[int, int, int]
