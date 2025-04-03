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


def player_setup():
    visible_cmp = cmp.Visible(glyph=display.Glyph.PLAYER, color=display.Color.GREEN)
    position_cmp = cmp.Position(x=1, y=1)
    actor = cmp.Actor(max_hp=10, name="player")
    esper.create_entity(cmp.Player(), position_cmp, visible_cmp, cmp.Blocking(), actor)

def main_menu_setup(context, console):
    render_proc = processors.MenuRenderProcessor(context, console)
    input_proc = processors.MenuInputEventProcessor()

    PHASES[Phase.menu] = [render_proc, input_proc]


def level_setup(context, console, game_board):
    input_proc = processors.GameInputEventProcessor()
    npc_proc = processors.NPCProcessor()
    damage_proc = processors.DamageProcessor()

    render_proc = processors.BoardRenderProcessor(console, context, game_board)
    movement_proc = processors.MovementProcessor(game_board)
    location.generate_dungeon(game_board)

    level_procs = [render_proc, input_proc, npc_proc, movement_proc, damage_proc]
    PHASES[Phase.level] = level_procs

def targeting_setup(context, console, game_board):
    pos = location.player_position()

    aoe_cmp = cmp.EffectArea(color=display.Color.RED)
    position_cmp = cmp.Position(x=pos.x, y=pos.y)
    esper.create_entity(cmp.Crosshair(), position_cmp, aoe_cmp)

    input_proc = processors.TargetInputEventProcessor(game_board)
    target_render_proc = processors.TargetRenderProcessor(console, context, game_board)
    movement_proc = processors.MovementProcessor(game_board)
    target_procs = [target_render_proc, input_proc, movement_proc]
    PHASES[Phase.target] = target_procs

def to_phase(phase: Phase, start_proc: type[esper.Processor]| None = None):
    """We dynamically add and remove processors when moving between phases. Each phase has its own proc loop."""
    for proc in esper._processors:
       esper.remove_processor(type(proc))
    esper._processors = []

    proc_list = PHASES[phase]
    if start_proc:
        idx = next((i for i, x in enumerate(proc_list) if isinstance(x, start_proc)))
        idx += 1
        proc_list = proc_list[idx:]+proc_list[:idx]
    for i, proc in enumerate(reversed(proc_list)):
        esper.add_processor(proc, priority=i)


def oneshot(proctype: type[esper.Processor]):
    proc_instance = esper.get_processor(proctype)
    if proc_instance:
        proc_instance.process()
