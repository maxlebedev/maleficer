# factories
import esper 

import components as cmp
import display
import location
import processors
import scene


def player():
    vis = cmp.Visible(glyph=display.Glyph.PLAYER, color=display.Color.GREEN)
    pos = cmp.Position(x=1, y=1)
    actor = cmp.Actor(max_hp=10, name="player")
    esper.create_entity(cmp.Player(), pos, vis, cmp.Blocking(), actor)


def inventory():
    esper.create_entity(cmp.InInventory(), cmp.Actor(name="bottle of water", max_hp=1))
    esper.create_entity(cmp.InInventory(), cmp.Actor(name="lighter", max_hp=1))


def main_menu(context, console):
    render_proc = processors.MenuRenderProcessor(context, console)
    input_proc = processors.MenuInputEventProcessor()

    scene.PHASES[scene.Phase.menu] = [render_proc, input_proc]


def level(context, console, game_board):
    input_proc = processors.GameInputEventProcessor()
    npc_proc = processors.NPCProcessor()
    damage_proc = processors.DamageProcessor()

    render_proc = processors.BoardRenderProcessor(console, context, game_board)
    movement_proc = processors.MovementProcessor(game_board)
    location.generate_dungeon(game_board)

    level_procs = [render_proc, input_proc, npc_proc, movement_proc, damage_proc]
    # do we want one damage phase or two?
    scene.PHASES[scene.Phase.level] = level_procs


def targeting(context, console, game_board):
    pos = location.player_position()

    aoe_cmp = cmp.EffectArea(color=display.Color.RED)
    position_cmp = cmp.Position(x=pos.x, y=pos.y)
    esper.create_entity(cmp.Crosshair(), position_cmp, aoe_cmp)

    input_proc = processors.TargetInputEventProcessor(game_board)
    target_render_proc = processors.TargetRenderProcessor(console, context, game_board)
    movement_proc = processors.MovementProcessor(game_board)
    target_procs = [target_render_proc, input_proc, movement_proc]
    scene.PHASES[scene.Phase.target] = target_procs


# TODO: should these take a position?
def floor(x: int, y: int) -> int:
    vis = cmp.Visible(glyph=display.Glyph.FLOOR, color=display.Color.LGREY)
    cell = esper.create_entity(
        cmp.Cell(), cmp.Position(x, y), vis, cmp.Transparent()
    )
    return cell

def wall(x: int, y: int) -> int:
    vis = cmp.Visible(glyph=display.Glyph.WALL, color=display.Color.LGREY)
    cell = esper.create_entity(cmp.Cell(), cmp.Position(x, y), vis, cmp.Blocking())
    return cell

def bat(pos: cmp.Position) -> int:
    vis = cmp.Visible(glyph=display.Glyph.BAT, color=display.Color.RED)
    actor = cmp.Actor(max_hp=1, name="bat")
    components = [cmp.Enemy(), pos, vis, cmp.Blocking(), actor, cmp.Wander()]
    bat = esper.create_entity(*components)
    return bat

def skeleton(pos: cmp.Position) -> int:
    vis = cmp.Visible(glyph=display.Glyph.SKELETON, color=display.Color.RED)
    actor = cmp.Actor(max_hp=3, name="skeleton")
    melee = cmp.Melee(radius=5)
    components = [cmp.Enemy(), pos, vis, cmp.Blocking(), actor, melee]
    skeleton = esper.create_entity(*components)
    return skeleton

def potion(pos: cmp.Position) -> int:
    vis = cmp.Visible(glyph=display.Glyph.POTION, color=display.Color.GREEN)
    col = cmp.Collectable()
    actor = cmp.Actor(max_hp=1, name="potion")
    components = [pos, vis, col, actor]
    potion = esper.create_entity(*components)
    return potion
