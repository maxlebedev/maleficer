import enum

import esper

import location
import components as cmp
import display
import processors

PHASES = dict()


class Phase(enum.Enum):
    menu = enum.auto()
    level = enum.auto()
    target = enum.auto()


def main_menu_setup(context, console):
    render_proc = processors.MenuRenderProcessor(context, console)
    input_proc = processors.MenuInputEventProcessor()

    PHASES[Phase.menu] = [input_proc, render_proc]


def level_setup(context, console, game_board):
    visible_cmp = cmp.Visible(glyph=display.Glyph.PLAYER, color=display.Color.GREEN)
    position_cmp = cmp.Position(x=1, y=1)
    actor = cmp.Actor(hp=10, name="player")
    esper.create_entity(cmp.Player(), position_cmp, visible_cmp, cmp.Blocking(), actor)
    input_proc = processors.GameInputEventProcessor()
    npc_proc = processors.NPCProcessor()
    damage_proc = processors.DamageProcessor()

    render_proc = processors.BoardRenderProcessor(console, context, game_board)
    movement_proc = processors.MovementProcessor(game_board)
    location.generate_dungeon(game_board)

    level_procs = [input_proc, npc_proc, damage_proc, render_proc, movement_proc]
    PHASES[Phase.level] = level_procs

def targeting_setup(context, console, game_board):
    pos = location.player_position()

    aoe_cmp = cmp.EffectArea(color=display.Color.RED)
    position_cmp = cmp.Position(x=pos.x, y=pos.y)
    esper.create_entity(cmp.Crosshair(), position_cmp, aoe_cmp)

    input_proc = processors.TargetInputEventProcessor()
    target_render_proc = processors.TargetRenderProcessor(console, context, game_board)
    movement_proc = processors.MovementProcessor(game_board)
    target_procs = [input_proc, target_render_proc, movement_proc]
    PHASES[Phase.target] = target_procs

def to_phase(phase: Phase):
    """We dynamically add and remove processors when moving between phases. Each phase has its own proc loop."""
    esper._processors = []
    for i, proc in enumerate(PHASES[phase]):
        esper.add_processor(proc, priority=i)
    return True  # returning True for InputEventProcessor reasons
