# type aliases

Entity = int

RGB = tuple[int, int, int]
CELL_RGB = tuple[int, RGB, RGB]

CELL = int
Coord = list[int]


class InvalidAction(Exception):
    pass
