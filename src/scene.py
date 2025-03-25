import enum

import esper

import board
import components as cmp
import display
import processors

PHASES = dict()


class Phase(enum.Enum):
    menu = enum.auto()
    board = enum.auto()
    target = enum.auto()


def main_menu_setup(context, console):
    render_proc = processors.MenuRenderProcessor(context, console)
    input_proc = processors.MenuInputEventProcessor()

    PHASES[Phase.menu] = [input_proc, render_proc]


def board_setup(context, console):
    visible_cmp = cmp.Visible(glyph=display.Glyph.PLAYER, color=display.Color.GREEN)
    position_cmp = cmp.Position(x=1, y=1)
    actor = cmp.Actor(hp=10, name="player")
    esper.create_entity(cmp.Player(), position_cmp, visible_cmp, cmp.Blocking(), actor)
    input_proc = processors.GameInputEventProcessor()
    npc_proc = processors.NPCProcessor()
    damage_proc = processors.DamageProcessor()

    game_board = board.Board()
    render_proc = processors.BoardRenderProcessor(console, context, game_board)
    movement_proc = processors.MovementProcessor(game_board)
    board.generate_dungeon(game_board)

    board_procs = [input_proc, npc_proc, damage_proc, render_proc, movement_proc]
    PHASES[Phase.board] = board_procs


def to_phase(phase: Phase):
    """We dynamically add and remove processors when moving between phases. Each phase has its own proc loop."""
    esper._processors = []
    for i, proc in enumerate(PHASES[phase]):
        esper.add_processor(proc, priority=i)
    return True  # returning True for InputEventProcessor reasons
