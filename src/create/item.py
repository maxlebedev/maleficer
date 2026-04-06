from functools import partial

import esper

import behavior
import components as cmp
import condition
import display as dis
import ecs
import location
import phase
import processors

from . import spell as create_spell


def potion(pos: cmp.Position | None = None) -> int:
    cmps = []
    cmps.append(cmp.Visible(glyph=dis.Glyph.POTION, color=dis.Color.GREEN))
    cmps.append(cmp.Collectable())
    cmps.append(cmp.Health(max=1))
    cmps.append(cmp.KnownAs(name="potion"))

    cmps.append(cmp.SpellEffect.Heal(amount=15))
    cmps.append(cmp.UseTrigger(callbacks=[behavior.apply_healing]))

    player = ecs.Query(cmp.Player).first()
    cmps.append(cmp.Target(target=player))
    potion = esper.create_entity(*cmps)
    if pos:
        esper.add_component(potion, pos)
    return potion


def scroll(pos: cmp.Position | None = None, spell: int | None = None) -> int:
    cmps = []
    cmps.append(cmp.Visible(glyph=dis.Glyph.SCROLL, color=dis.Color.MAGENTA))
    cmps.append(cmp.Collectable())
    cmps.append(cmp.Health(max=1))

    map_info = ecs.Query(cmp.GameMeta).cmp(cmp.MapInfo)

    if not spell:
        power_budget = 10 + (map_info.depth * 5)
        spell = create_spell.ProcGen.new(power_budget=power_budget)
    cmps.append(cmp.Learnable(spell=spell))
    cmps.append(cmp.UseTrigger(callbacks=[behavior.apply_learn]))

    scroll = esper.create_entity(*cmps)
    if pos:
        esper.add_component(scroll, pos)

    spell_name = esper.component_for_entity(spell, cmp.KnownAs).name
    known_as = cmp.KnownAs(name=f"{spell_name} scroll")
    esper.add_component(scroll, known_as)
    return scroll


def bomb(pos: cmp.Position) -> int:
    cmps = []
    cmps.append(pos)
    cmps.append(cmp.Visible(glyph=dis.Glyph.BOMB, color=dis.Color.RED))
    cmps.append(cmp.Health(max=1))
    cmps.append(cmp.KnownAs(name="bomb"))
    cmps.append(cmp.Enemy(evaluate=behavior.bomb))
    callback = partial(location.coords_within_radius, radius=1)
    cmps.append(cmp.EffectArea(callback))

    cmps.append(cmp.Aura(callback=callback, color=dis.Color.LIGHT_RED))

    dmg_proc = lambda _: phase.oneshot(processors.Damage)
    cmps.append(cmp.DeathTrigger(callbacks=[behavior.apply_damage, dmg_proc]))

    bomb_ent = esper.create_entity(*cmps)
    dmg = cmp.SpellEffect.Damage(source=bomb_ent, amount=10)
    esper.add_component(bomb_ent, dmg)
    condition.grant(bomb_ent, cmp.Condition.Dying, 2)

    return bomb_ent


def spike_trap(pos: cmp.Position) -> int:
    cmps = []
    cmps.append(pos)
    cmps.append(cmp.Visible(glyph=dis.Glyph.TRAP, color=dis.Color.RED))
    cmps.append(cmp.Health(max=1))
    cmps.append(cmp.KnownAs(name="spike trap"))

    cmps.append(cmp.StepTrigger(callbacks=[behavior.apply_damage]))
    trap_ent = esper.create_entity(*cmps)
    dmg = cmp.SpellEffect.Damage(source=trap_ent, amount=5)
    esper.add_component(trap_ent, dmg)
    return trap_ent


def bomb_trap(pos: cmp.Position) -> int:
    cmps = []
    cmps.append(pos)
    cmps.append(cmp.Health(max=1))
    cmps.append(cmp.Visible(glyph=dis.Glyph.TRAP, color=dis.Color.RED))
    cmps.append(cmp.KnownAs(name="bomb trap"))

    cmps.append(cmp.StepTrigger(callbacks=[behavior.die]))
    cmps.append(cmp.DeathTrigger(callbacks=[behavior.spawn_bomb]))
    trap_ent = esper.create_entity(*cmps)

    return trap_ent


def poison_trap(pos: cmp.Position) -> int:
    cmps = []
    cmps.append(pos)
    cmps.append(cmp.Health(max=1))
    cmps.append(cmp.Visible(glyph=dis.Glyph.TRAP, color=dis.Color.RED))
    cmps.append(cmp.KnownAs(name="poison trap"))

    cmps.append(cmp.StepTrigger(callbacks=[behavior.die]))
    cmps.append(cmp.DeathTrigger(callbacks=[behavior.spawn_poison_cloud]))
    trap_ent = esper.create_entity(*cmps)

    return trap_ent

def poison_cloud(pos: cmp.Position):
    cmps = []
    cmps.append(pos)
    cmps.append(cmp.Visible(glyph=dis.Glyph.CLOUD, color=dis.Color.GREEN))
    cmps.append(cmp.KnownAs(name="poison cloud"))
    cmps.append(cmp.Condition.Dying(value=5))

    # TODO: technically bats are immune
    cmps.append(cmp.StepTrigger(callbacks=[behavior.apply_damage]))
    cloud = esper.create_entity(*cmps)
    dmg = cmp.SpellEffect.Damage(source=cloud, amount=5)
    esper.add_component(cloud, dmg)

    return cloud



def grass(pos: cmp.Position) -> int:
    cmps = []
    cmps.append(pos)
    cmps.append(cmp.Visible(glyph=dis.Glyph.GRASS, color=dis.Color.DARK_GREEN))
    cmps.append(cmp.Health(max=1))
    cmps.append(cmp.KnownAs(name="grass"))
    cmps.append(cmp.Opaque())

    cmps.append(cmp.StepTrigger(callbacks=[behavior.die]))
    trap_ent = esper.create_entity(*cmps)
    return trap_ent

def flare_charge(pos: cmp.Position | None = None) -> int:
    # TODO: should both this and flare spell exist?
    cmps = []
    cmps.append(cmp.Visible(glyph=dis.Glyph.POTION, color=dis.Color.MAGENTA))
    cmps.append(cmp.Health(max=1))
    cmps.append(cmp.KnownAs(name="flare charge"))
    cmps.append(cmp.Collectable())
    cmps.append(pos)

    callback = partial(behavior.place_on_unoccupied, spawn=sensor, count=3)
    cmps.append(cmp.UseTrigger(callbacks=[callback]))
    return esper.create_entity(*cmps)

def sensor(pos: cmp.Position | None = None) -> int:
    cmps = []
    cmps.append(cmp.Health(max=1))
    cmps.append(cmp.KnownAs(name="sensor"))
    cmps.append(pos)
    cmps.append(cmp.GivesVision(distance=4))
    return esper.create_entity(*cmps)
