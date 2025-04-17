import enum
import copy

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


# do I want this to be in create.py?
def player_setup():
    vis = cmp.Visible(glyph=display.Glyph.PLAYER, color=display.Color.GREEN)
    pos = cmp.Position(x=1, y=1)
    actor = cmp.Actor(max_hp=10)
    named = cmp.Onymous(name="player")
    esper.create_entity(cmp.Player(), pos, vis, cmp.Blocking(), actor, named)


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


def level_phase(context, console, game_board):
    upkeep = processors.UpkeepProcessor()

    render = processors.BoardRenderProcessor(console, context, game_board)
    input = processors.GameInputEventProcessor()
    npc = processors.NPCProcessor()

    movement = processors.MovementProcessor(game_board)
    damage = processors.DamageProcessor()
    location.generate_dungeon(game_board)

    level_procs = [upkeep, render, input, npc, movement, damage]
    # do we want one damage phase or two?
    PHASES[Phase.level] = level_procs


def targeting_phase(context, console, game_board):
    pos = location.player_position()

    aoe_cmp = cmp.EffectArea(color=display.Color.RED)
    position_cmp = cmp.Position(x=pos.x, y=pos.y)
    esper.create_entity(cmp.Crosshair(), position_cmp, aoe_cmp)

    input = processors.TargetInputEventProcessor(game_board)
    target_render = processors.TargetRenderProcessor(console, context, game_board)
    movement = processors.MovementProcessor(game_board)
    PHASES[Phase.target] = [target_render, input, movement]


def inventory_phase(context, console, game_board):
    esper.create_entity(cmp.MenuSelection())

    input = processors.InventoryInputEventProcessor()
    render = processors.InventoryRenderProcessor(console, context, game_board)

    PHASES[Phase.inventory] = [render, input]


def to_phase(phase: Phase, start_proc: type[esper.Processor] | None = None):
    """We dynamically add and remove processors when moving between phases. Each phase has its own proc loop."""
    for proc in esper._processors:
        esper.remove_processor(type(proc))
    esper._processors = []

    proc_list = copy.copy(PHASES[phase]) # copy to prevent mutation of original
    if start_proc:
        while start_proc and not isinstance(proc_list[0], start_proc):
            proc_list.append(proc_list.pop(0))

    proc_list = list(reversed(proc_list))
    for i, proc in enumerate(proc_list):
        esper.add_processor(proc, priority=i)


def oneshot(proctype: type[esper.Processor]):
    """only works on processors that are already registered"""
    if proc_instance:= esper.get_processor(proctype):
        proc_instance.process()
