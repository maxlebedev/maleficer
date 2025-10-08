import random
import string
from functools import partial

import esper

import behavior
import components as cmp
import ecs
import location


# TODO: maybe it takes a level as well as power budget
# some effects may only be available at some levels
# big refactor time
class ProcGen():

    @classmethod
    def _spell_stats(cls, power_budget=10, waste_chance=0.2) -> tuple[int, int, int]:
        stats = {"damage": 1, "range": 2, "cooldown": 1}
        remaining_points = power_budget - sum(stats.values())
        while remaining_points > 0:
            if random.random() > waste_chance:
                stat = random.choice(list(stats.keys()))
                stats[stat] += 1
            remaining_points -= 1
        stats["cooldown"] = max(1, 5 - stats["cooldown"])
        stats["damage"] *= 10
        return stats["damage"], stats["range"], stats["cooldown"]

    @classmethod
    def new(cls, power_budget) -> int:
        waste_chance = 0.2
        match random.randint(0, 3):
            case 0:
                waste_chance = 0.4
        damage, target_range, cooldown = cls._spell_stats(power_budget, waste_chance)

        player = ecs.Query(cmp.Player).first()
        spell_cmp = cmp.Spell(target_range=target_range)
        cooldown = cmp.Cooldown(turns=cooldown)
        ut = cmp.UseTrigger(callbacks=[behavior.apply_cooldown])
        if waste_chance == 0.4:
            harm_effect = cmp.BleedEffect(value=damage)
            ut.callbacks.append(behavior.apply_bleed)
        else:
            harm_effect = cmp.DamageEffect(amount=damage, source=player)
            ut.callbacks.append(behavior.apply_damage)
        name = "".join(random.choices(string.ascii_lowercase, k=5))
        named = cmp.Onymous(name=name)
        spell = esper.create_entity(spell_cmp, harm_effect, named, cooldown, ut)

        match random.randint(0, 6):
            # TODO: pull this into the power budget calculation
            case 0:
                radius = random.randint(1, target_range - 1)

                callback = partial(location.coords_within_radius, radius=radius)
                esper.add_component(spell, cmp.EffectArea(callback))
        return spell


# all these prefab spells need a power input

def firebolt(level=1) -> int:
    cmps = []
    player = ecs.Query(cmp.Player).first()
    cmps.append(cmp.Spell(target_range=5))
    cmps.append(cmp.Cooldown(turns=1))
    cmps.append(cmp.DamageEffect(amount=1+level, die_type=6, source=player))
    callback = partial(location.coords_within_radius, radius=1)
    cmps.append(cmp.EffectArea(callback))
    cmps.append(cmp.Onymous(name="Firebolt"))
    callbacks = [behavior.apply_cooldown, behavior.apply_damage]
    cmps.append(cmp.UseTrigger(callbacks=callbacks))

    return esper.create_entity(*cmps)


def blink(level=1) -> int:
    cmps = []
    player = ecs.Query(cmp.Player).first()
    cmps.append(cmp.Spell(target_range=3+level))
    cmps.append(cmp.Cooldown(turns=5))
    callbacks = [behavior.apply_cooldown, behavior.apply_move]
    cmps.append(cmp.UseTrigger(callbacks=callbacks))
    cmps.append(cmp.MoveEffect(target=player))
    cmps.append(cmp.Onymous(name="Blink"))

    return esper.create_entity(*cmps)


def bleed(level=1) -> int:
    cmps = []
    cmps.append(cmp.Spell(target_range=3))
    cmps.append(cmp.Cooldown(turns=2))
    cmps.append(cmp.BleedEffect(value=4+level))
    callbacks = [behavior.apply_cooldown, behavior.apply_bleed]
    cmps.append(cmp.UseTrigger(callbacks=callbacks))
    cmps.append(cmp.Onymous(name="Lacerate"))

    return esper.create_entity(*cmps)


def push(level=1) -> int:
    cmps = []
    cmps.append(cmp.Spell(target_range=3+level))
    cmps.append(cmp.Cooldown(turns=2))
    callbacks = [behavior.apply_cooldown, behavior.apply_push]
    cmps.append(cmp.UseTrigger(callbacks=callbacks))
    cmps.append(cmp.Onymous(name="Push"))

    player = ecs.Query(cmp.Player).first()
    cmps.append(cmp.PushEffect(source=player, distance=2))

    return esper.create_entity(*cmps)


def daze(level=1) -> int:
    cmps = []
    cmps.append(cmp.Spell(target_range=2))
    cmps.append(cmp.Cooldown(turns=6))
    callbacks = [behavior.apply_cooldown, behavior.apply_stun]
    cmps.append(cmp.UseTrigger(callbacks=callbacks))
    cmps.append(cmp.Onymous(name="Daze"))
    cmps.append(cmp.StunEffect(value=1+level))

    return esper.create_entity(*cmps)


def shield(level=1) -> int:
    cmps = []
    cmps.append(cmp.Spell(target_range=0))
    cmps.append(cmp.Cooldown(turns=6))
    callbacks = [behavior.apply_cooldown, behavior.apply_aegis]
    cmps.append(cmp.UseTrigger(callbacks=callbacks))
    cmps.append(cmp.Onymous(name="Shield"))
    cmps.append(cmp.AegisEffect(value=9 + level))

    return esper.create_entity(*cmps)
