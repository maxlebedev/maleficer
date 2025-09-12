# game loops
import copy
import enum

import esper

import create
import components as cmp
import location
import processors

ALL = dict()
CURRENT = None


class Ontology(enum.Enum):
    menu = enum.auto()
    options = enum.auto()
    about = enum.auto()
    level = enum.auto()
    target = enum.auto()
    inventory = enum.auto()
    start = enum.auto()


def main_menu_phase(context, console):
    render = processors.MenuRender(context, console)
    input = processors.MenuInputEvent()

    ALL[Ontology.menu] = [render, input]
    create.ui.main_menu_opts()


def level_phase(context, console):
    upkeep = processors.Upkeep()

    render = processors.BoardRender(console, context)
    input = processors.GameInputEvent()
    npc = processors.NPCTurn()

    player_movement = processors.Movement()
    movement = processors.Movement()
    player_dmg = processors.Damage()
    npc_dmg = processors.Damage()
    death = processors.Death()

    level_procs = [
        upkeep,
        render,
        input,
        player_dmg,
        player_movement,
        npc,
        movement,
        npc_dmg,
        death,
    ]
    ALL[Ontology.level] = level_procs


def targeting_phase(context, console):
    pos = location.player_position()

    position_cmp = cmp.Position(x=pos.x, y=pos.y)
    esper.create_entity(cmp.Crosshair(), position_cmp)

    input = processors.TargetInputEvent()
    target_render = processors.TargetRender(console, context)
    movement = processors.Movement()
    ALL[Ontology.target] = [target_render, input, movement]


def inventory_phase(context, console):
    esper.create_entity(cmp.MenuSelection())

    input = processors.InventoryInputEvent()
    render = processors.InventoryRender(console, context)

    ALL[Ontology.inventory] = [render, input]


def options_phase(context, console):
    render = processors.OptionsRender(context, console)
    input = processors.OptionsInputEvent()

    ALL[Ontology.options] = [render, input]


def about_phase(context, console):
    render = processors.AboutRender(context, console)
    input = processors.AboutInputEvent()

    ALL[Ontology.about] = [render, input]


def start_phase(context, console):
    render = processors.StartRender(context, console)
    input = processors.MenuInputEvent()

    ALL[Ontology.start] = [render, input]
    create.ui.start_opts()


def change_to(phase: Ontology, start_proc: type[esper.Processor] | None = None):
    """We dynamically add and remove processors when moving between phases. Each phase has its own proc loop."""
    global CURRENT
    for proc in esper._processors:
        esper.remove_processor(type(proc))
    esper._processors = []

    proc_list = copy.copy(ALL[phase])  # copy to prevent mutation of original
    if start_proc:
        while start_proc and not isinstance(proc_list[0], start_proc):
            proc_list.append(proc_list.pop(0))

    tot_procs = len(proc_list)
    for i, proc in enumerate(proc_list):
        esper.add_processor(proc, priority=tot_procs - i)
    CURRENT = phase


def oneshot(proctype: type[esper.Processor]):
    """only works on processors that are already registered"""
    if proc_instance := esper.get_processor(proctype):
        proc_instance.process()
