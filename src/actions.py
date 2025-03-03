from dataclasses import dataclass

class Action:
    pass


@dataclass
class MovementAction(Action):
    dx: int
    dy: int
