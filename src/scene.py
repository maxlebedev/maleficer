import copy
import enum

import esper

import components as cmp
import display
import location
import processors

PHASES = dict()


class Phase(enum.Enum):
    menu = enum.auto()
    level = enum.auto()
    target = enum.auto()
    inventory = enum.auto()


def inventory_setup():
    esper.create_entity(
        cmp.InInventory(), cmp.Actor(max_hp=1), cmp.Onymous(name="bottle of water")
    )
    esper.create_entity(
        cmp.InInventory(), cmp.Actor(max_hp=1), cmp.Onymous(name="lighter")
    )


def main_menu_phase(context, console):
    render = processors.MenuRenderProcessor(context, console)
    input = processors.MenuInputEventProcessor()

    PHASES[Phase.menu] = [render, input]


def level_phase(context, console):
    upkeep = processors.UpkeepProcessor()

    render = processors.BoardRenderProcessor(console, context)
    input = processors.GameInputEventProcessor()
    npc = processors.NPCProcessor()

    movement = processors.MovementProcessor()
    damage = processors.DamageProcessor()

    level_procs = [upkeep, render, input, npc, movement, damage]
    # do we want one damage phase or two?
    PHASES[Phase.level] = level_procs


def targeting_phase(context, console):
    pos = location.player_position()

    aoe_cmp = cmp.EffectArea(color=display.Color.RED)
    position_cmp = cmp.Position(x=pos.x, y=pos.y)
    esper.create_entity(cmp.Crosshair(), position_cmp, aoe_cmp)

    input = processors.TargetInputEventProcessor()
    target_render = processors.TargetRenderProcessor(console, context)
    movement = processors.MovementProcessor()
    PHASES[Phase.target] = [target_render, input, movement]


def inventory_phase(context, console):
    esper.create_entity(cmp.MenuSelection())

    input = processors.InventoryInputEventProcessor()
    render = processors.InventoryRenderProcessor(console, context)

    PHASES[Phase.inventory] = [render, input]


def to_phase(phase: Phase, start_proc: type[esper.Processor] | None = None):
    """We dynamically add and remove processors when moving between phases. Each phase has its own proc loop."""
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


def oneshot(proctype: type[esper.Processor]):
    """only works on processors that are already registered"""
    if proc_instance := esper.get_processor(proctype):
        proc_instance.process()
