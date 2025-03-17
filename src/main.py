from enum import IntEnum, StrEnum

import esper
import tcod

import display
import scene


def main() -> None:

    manager = scene.Manager()

    manager.change_scene(scene.State.GAME)
    esper.delete_world("default")

    manager.current_scene.setup()

    # esper.set_handler("target", input.Target.perform)

    while True:
        esper.process()


if __name__ == "__main__":
    main()
