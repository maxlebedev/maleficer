import esper
from functools import partial

import behavior
import components as cmp
import display as dis
import ecs
import location
import scene
from . import spell as create_spell
import condition
import typ
import processors


def potion(pos: cmp.Position | None = None) -> int:
    cmps = []
    cmps.append(cmp.Visible(glyph=dis.Glyph.POTION, color=dis.Color.GREEN))
    cmps.append(cmp.Collectable())
    cmps.append(cmp.Health(max=1))
    cmps.append(cmp.Onymous(name="potion"))

    cmps.append(cmp.HealEffect(amount=2))
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

    if not spell:
        spell = create_spell.new(5 + (location.LEVEL * 5))
    cmps.append(cmp.Learnable(spell=spell))
    cmps.append(cmp.UseTrigger(callbacks=[behavior.apply_learn]))

    scroll = esper.create_entity(*cmps)
    if pos:
        esper.add_component(scroll, pos)

    spell_name = esper.component_for_entity(spell, cmp.Onymous).name
    named = cmp.Onymous(name=f"{spell_name} scroll")
    esper.add_component(scroll, named)
    return scroll


def bomb(pos: cmp.Position) -> int:
    cmps = []
    cmps.append(pos)
    cmps.append(cmp.Visible(glyph=dis.Glyph.BOMB, color=dis.Color.RED))
    cmps.append(cmp.Health(max=1))
    cmps.append(cmp.Onymous(name="bomb"))
    cmps.append(cmp.OnDeath())
    cmps.append(cmp.Enemy())
    callback = partial(location.coords_within_radius, radius=1)
    cmps.append(cmp.EffectArea(callback))
    cmps.append(cmp.Aura(radius=1, color=dis.Color.WHITE))

    dmg_proc = lambda _: scene.oneshot(processors.Damage)
    cmps.append(cmp.DeathTrigger(callbacks=[behavior.apply_damage, dmg_proc]))

    def aura_tick(entity: int):
        aura = esper.component_for_entity(entity, cmp.Aura)
        match aura.color:
            case dis.Color.WHITE:
                aura.color = dis.Color.LIGHT_RED
            case dis.Color.LIGHT_RED:
                aura.color = dis.Color.BLOOD_RED

    cmps.append(cmp.EnemyTrigger(callbacks=[aura_tick]))

    bomb_ent = esper.create_entity(*cmps)
    dmg = cmp.DamageEffect(source=bomb_ent, amount=1)
    esper.add_component(bomb_ent, dmg)
    condition.grant(bomb_ent, typ.Condition.Dying, 2)

    return bomb_ent


def trap(pos: cmp.Position) -> int:
    cmps = []
    cmps.append(pos)
    cmps.append(cmp.Visible(glyph=dis.Glyph.TRAP, color=dis.Color.RED))
    cmps.append(cmp.Health(max=1))
    cmps.append(cmp.Onymous(name="trap"))
    cmps.append(cmp.OnStep())

    cmps.append(cmp.StepTrigger(callbacks=[behavior.apply_damage]))
    trap_ent = esper.create_entity(*cmps)
    dmg = cmp.DamageEffect(source=trap_ent, amount=1)
    esper.add_component(trap_ent, dmg)
    return trap_ent
