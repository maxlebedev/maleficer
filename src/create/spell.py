import random
import string
from functools import partial

import esper

import components as cmp
import ecs
import location


# TODO: maybe it takes a level as well as power budget
# some effects may only be available at some levels
class ProcGen:
    # power_budget: 10, 15, 20, 25

    @classmethod
    def named_spell(cls, power_budget: int) -> int:
        """generate a named spell of a lvl-appropriate rank"""
        spell_rank = 1 + power_budget // 10
        foo = [firebolt, lacerate, daze, blink, push, shield, lighting]
        spell = random.choice(foo)
        return spell(spell_rank, name=f"{foo[0].__name__.title()} {spell_rank}")

    @classmethod
    def make_damage_effect(cls, power_budget: int):
        player = ecs.Query(cmp.Player).first()
        amount = max(2, power_budget // 5)
        return cmp.DamageEffect(amount=amount, die_type=6, source=player)

    @classmethod
    def make_push_effect(cls, power_budget: int):
        player = ecs.Query(cmp.Player).first()
        distance = max(1, power_budget // 5)
        return cmp.PushEffect(distance=distance, source=player)

    @classmethod
    def make_stun_effect(cls, power_budget: int):
        value = max(1, power_budget // 5)
        return cmp.StunEffect(value=value)

    @classmethod
    def make_bleed_effect(cls, power_budget: int):
        return cmp.BleedEffect(value=power_budget)

    @classmethod
    def make_area_effect(cls, power_budget: int):
        radius = max(1, power_budget // 5)
        callback = partial(location.coords_within_radius, radius=radius)
        return cmp.EffectArea(callback)

    @classmethod
    def combat(cls, power_budget: int) -> int:
        """a spell that effects enemies"""
        rank = power_budget // 5

        remaining_budget = power_budget
        effect_pool = [
            (cls.make_stun_effect),
            (cls.make_bleed_effect),
            (cls.make_damage_effect),
            (cls.make_push_effect),
        ]
        effects = []
        # okay, so I don't want to have damage alone, or mostly range
        for _ in range(round(random.triangular(1, 3, 2))):
            idx = random.randint(0, len(effect_pool) - 1)
            effect = effect_pool.pop(idx)
            # TODO: we want more variance than always rank here
            value = remaining_budget // 2
            effects.append(effect(power_budget=value))
            remaining_budget -= value

            if len(effects) == 1:
                effect_pool.append(cls.make_area_effect)

        target_range = max(2, remaining_budget)
        cooldown = max(3, rank + random.randint(-3, 3))

        spell = cls._effects_to_spell(effects, target_range, cooldown)
        return spell

    @classmethod
    def _effects_to_spell(cls, effects: list, target_range: int, cooldown: int):
        spell_cmp = cmp.Spell(target_range=target_range)
        cooldown_cmp = cmp.Cooldown(turns=cooldown)
        name = "".join(random.choices(string.ascii_lowercase, k=5))
        named = cmp.Onymous(name=name)
        spell = esper.create_entity(spell_cmp, named, cooldown_cmp, *effects)
        return spell

    @classmethod
    def new(cls, power_budget: int) -> int:
        map_info = ecs.Query(cmp.GameMeta).cmp(cmp.MapInfo)
        if map_info.depth > 1 and not random.randint(0, 5):
            return cls.named_spell(power_budget)

        spell = cls.combat(power_budget)
        # TODO: utility spell func as well, with Aegis, Move, etc
        return spell


def firebolt(level=1, name="Firebolt") -> int:
    cmps = []
    player = ecs.Query(cmp.Player).first()
    cmps.append(cmp.Spell(target_range=5))
    cmps.append(cmp.Cooldown(turns=1))
    cmps.append(cmp.DamageEffect(amount=1 + level, die_type=6, source=player))
    callback = partial(location.coords_within_radius, radius=1)
    cmps.append(cmp.EffectArea(callback))
    cmps.append(cmp.Onymous(name=name))

    return esper.create_entity(*cmps)


def lighting(level=1, name="Lighting") -> int:
    cmps = []
    player = ecs.Query(cmp.Player).first()
    cmps.append(cmp.Spell(target_range=5))
    cmps.append(cmp.Cooldown(turns=5))
    cmps.append(cmp.DamageEffect(amount=4 + level, die_type=6, source=player))

    player_pos = location.player_position()
    callback = partial(location.coords_line_to_point, player_pos)
    cmps.append(cmp.EffectArea(callback))
    cmps.append(cmp.Onymous(name=name))

    return esper.create_entity(*cmps)


def blink(level=1, name="Blink") -> int:
    cmps = []
    player = ecs.Query(cmp.Player).first()
    cmps.append(cmp.Spell(target_range=3 + level))
    cmps.append(cmp.Cooldown(turns=5))
    cmps.append(cmp.MoveEffect(target=player))
    cmps.append(cmp.Onymous(name=name))

    return esper.create_entity(*cmps)


def lacerate(level=1, name="Lacerate") -> int:
    cmps = []
    cmps.append(cmp.Spell(target_range=3))
    cmps.append(cmp.Cooldown(turns=2))
    cmps.append(cmp.BleedEffect(value=4 + level))
    cmps.append(cmp.Onymous(name=name))

    return esper.create_entity(*cmps)


def push(level=1, name="Push") -> int:
    cmps = []
    cmps.append(cmp.Spell(target_range=3 + level))
    cmps.append(cmp.Cooldown(turns=2))
    cmps.append(cmp.Onymous(name=name))

    player = ecs.Query(cmp.Player).first()
    cmps.append(cmp.PushEffect(source=player, distance=2))

    return esper.create_entity(*cmps)


def pull(level=1, name="Pull") -> int:
    cmps = []
    spell_range = 3 + level
    cmps.append(cmp.Spell(target_range=spell_range))
    cmps.append(cmp.Cooldown(turns=2))
    cmps.append(cmp.Onymous(name=name))

    player = ecs.Query(cmp.Player).first()
    cmps.append(cmp.PullEffect(source=player, distance=spell_range))

    return esper.create_entity(*cmps)


def daze(level=1, name="Daze") -> int:
    cmps = []
    cmps.append(cmp.Spell(target_range=2))
    cmps.append(cmp.Cooldown(turns=6))
    cmps.append(cmp.Onymous(name=name))
    cmps.append(cmp.StunEffect(value=1 + level))

    return esper.create_entity(*cmps)


def shield(level=1, name="Shield") -> int:
    cmps = []
    cmps.append(cmp.Spell(target_range=0))
    cmps.append(cmp.Cooldown(turns=6))
    cmps.append(cmp.Onymous(name=name))
    cmps.append(cmp.AegisEffect(value=9 + level))

    return esper.create_entity(*cmps)
