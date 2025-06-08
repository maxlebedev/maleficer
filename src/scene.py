import copy
import enum

import esper

import components as cmp
import display
import location
import processors

PHASES = dict()
CURRENT_PHASE = None


class Phase(enum.Enum):
    menu = enum.auto()
    options = enum.auto()
    level = enum.auto()
    target = enum.auto()
    inventory = enum.auto()


def main_menu_phase(context, console):
    render = processors.MenuRender(context, console)
    input = processors.MenuInputEvent()

    PHASES[Phase.menu] = [render, input]


def level_phase(context, console):
    upkeep = processors.Upkeep()

    render = processors.BoardRender(console, context)
    input = processors.GameInputEvent()
    npc = processors.NPCTurn()

    movement = processors.Movement()
    player_dmg = processors.Damage()
    npc_dmg = processors.Damage()
    death = processors.Death()

    level_procs = [upkeep, render, input, player_dmg, npc, movement, npc_dmg, death]
    PHASES[Phase.level] = level_procs


def targeting_phase(context, console):
    pos = location.player_position()

    position_cmp = cmp.Position(x=pos.x, y=pos.y)
    esper.create_entity(cmp.Crosshair(), position_cmp)

    input = processors.TargetInputEvent()
    target_render = processors.TargetRender(console, context)
    movement = processors.Movement()
    PHASES[Phase.target] = [target_render, input, movement]


def inventory_phase(context, console):
    esper.create_entity(cmp.MenuSelection())

    input = processors.InventoryInputEvent()
    render = processors.InventoryRender(console, context)

    PHASES[Phase.inventory] = [render, input]


def options_phase(context, console):
    render = processors.OptionsRender(context, console)
    input = processors.OptionsInputEvent()

    PHASES[Phase.options] = [render, input]


def to_phase(phase: Phase, start_proc: type[esper.Processor] | None = None):
    """We dynamically add and remove processors when moving between phases. Each phase has its own proc loop."""
    global CURRENT_PHASE
    for proc in esper._processors:
        esper.remove_processor(type(proc))
    esper._processors = []

    proc_list = copy.copy(PHASES[phase])  # copy to prevent mutation of original
    if start_proc:
        while start_proc and not isinstance(proc_list[0], start_proc):
            proc_list.append(proc_list.pop(0))

    proc_list = list(reversed(proc_list))
    for i, proc in enumerate(proc_list):
        esper.add_processor(proc, priority=i)
    CURRENT_PHASE = phase


def oneshot(proctype: type[esper.Processor]):
    """only works on processors that are already registered"""
    if proc_instance := esper.get_processor(proctype):
        proc_instance.process()
