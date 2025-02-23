from dataclasses import dataclass as component


@component
class Player:
    pass

@component
class Position:
    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y

@component
class Movement:
    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y
