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


# do I want this to be in create.py?
def player_setup():
    vis = cmp.Visible(glyph=display.Glyph.PLAYER, color=display.Color.GREEN)
    pos = cmp.Position(x=1, y=1)
    actor = cmp.Actor(max_hp=10, name="player")
    esper.create_entity(cmp.Player(), pos, vis, cmp.Blocking(), actor)


def inventory_setup():
    esper.create_entity(cmp.InInventory(), cmp.Actor(name="bottle of water", max_hp=1))
    esper.create_entity(cmp.InInventory(), cmp.Actor(name="lighter", max_hp=1))


def main_menu_phase(context, console):
    render_proc = processors.MenuRenderProcessor(context, console)
    input_proc = processors.MenuInputEventProcessor()

    PHASES[Phase.menu] = [render_proc, input_proc]


def level_phase(context, console, game_board):
    input_proc = processors.GameInputEventProcessor()
    npc_proc = processors.NPCProcessor()
    damage_proc = processors.DamageProcessor()

    render_proc = processors.BoardRenderProcessor(console, context, game_board)
    movement_proc = processors.MovementProcessor(game_board)
    location.generate_dungeon(game_board)

    level_procs = [render_proc, input_proc, npc_proc, movement_proc, damage_proc]
    # do we want one damage phase or two?
    PHASES[Phase.level] = level_procs


def targeting_phase(context, console, game_board):
    pos = location.player_position()

    aoe_cmp = cmp.EffectArea(color=display.Color.RED)
    position_cmp = cmp.Position(x=pos.x, y=pos.y)
    esper.create_entity(cmp.Crosshair(), position_cmp, aoe_cmp)

    input_proc = processors.TargetInputEventProcessor(game_board)
    target_render_proc = processors.TargetRenderProcessor(console, context, game_board)
    movement_proc = processors.MovementProcessor(game_board)
    target_procs = [target_render_proc, input_proc, movement_proc]
    PHASES[Phase.target] = target_procs


def inventory_phase(context, console, game_board):
    esper.create_entity(cmp.MenuSelection())

    input_proc = processors.InventoryInputEventProcessor()
    render_proc = processors.InventoryRenderProcessor(console, context, game_board)

    inventory_procs = [render_proc, input_proc]
    PHASES[Phase.inventory] = inventory_procs


def to_phase(phase: Phase, start_proc: type[esper.Processor] | None = None):
    """We dynamically add and remove processors when moving between phases. Each phase has its own proc loop."""
    for proc in esper._processors:
        esper.remove_processor(type(proc))
    esper._processors = []

    proc_list = PHASES[phase]
    if start_proc:
        while start_proc and not isinstance(proc_list[0], start_proc):
            proc_list.append(proc_list.pop(0))

    proc_list = list(reversed(proc_list))
    for i, proc in enumerate(proc_list):
        esper.add_processor(proc, priority=i)


def oneshot(proctype: type[esper.Processor]):
    """only works on processors that are already registered"""
    proc_instance = esper.get_processor(proctype)
    if proc_instance:
        proc_instance.process()
