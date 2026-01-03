import esper

import behavior
import components as cmp
import display as dis


def bat(pos: cmp.Position) -> int:
    cmps = []
    cmps.append(pos)
    cmps.append(cmp.Visible(glyph=dis.Glyph.BAT, color=dis.Color.BROWN))
    cmps.append(cmp.Health(max=10))
    cmps.append(cmp.KnownAs(name="bat"))
    cmps.append(cmp.Flying())
    cmps.append(cmp.Enemy(evaluate=behavior.bat))
    cmps.append(cmp.Blocking())
    bat = esper.create_entity(*cmps)

    dmg_effect = cmp.DamageEffect(amount=5, source=bat)
    esper.add_component(bat, dmg_effect)
    return bat


def skeleton(pos: cmp.Position) -> int:
    cmps = []
    cmps.append(pos)
    cmps.append(cmp.Visible(glyph=dis.Glyph.SKELETON, color=dis.Color.BEIGE))
    cmps.append(cmp.Health(max=25))
    cmps.append(cmp.KnownAs(name="skeleton"))
    cmps.append(cmp.Enemy(perception=10, evaluate=behavior.skeleton))
    cmps.append(cmp.Blocking())
    skeleton = esper.create_entity(*cmps)

    dmg_effect = cmp.DamageEffect(amount=10, source=skeleton)
    esper.add_component(skeleton, dmg_effect)
    return skeleton


def warlock(pos: cmp.Position) -> int:
    cmps = []
    cmps.append(pos)

    cmps.append(cmp.Visible(glyph=dis.Glyph.WARLOCK, color=dis.Color.INDIGO))
    cmps.append(cmp.Health(max=15))
    cmps.append(cmp.KnownAs(name="warlock"))
    cmps.append(cmp.Cooldown(turns=1))
    cmps.append(cmp.Enemy(perception=3, evaluate=behavior.warlock))
    cmps.append(cmp.Blocking())
    warlock = esper.create_entity(*cmps)

    dmg_effect = cmp.DamageEffect(amount=5, source=warlock)
    esper.add_component(warlock, dmg_effect)
    return warlock


# TODO: add move animations
def living_flame(pos: cmp.Position) -> int:
    """melee unit, with a dash"""
    cmps = []
    cmps.append(pos)
    cmps.append(cmp.Visible(glyph=dis.Glyph.FLAME, color=dis.Color.ORANGE))
    cmps.append(cmp.Health(max=20))
    cmps.append(cmp.KnownAs(name="living flame"))
    cmps.append(cmp.Enemy(speed=2, perception=5, evaluate=behavior.living_flame))
    cmps.append(cmp.Blocking())
    flame = esper.create_entity(*cmps)

    dmg_effect = cmp.DamageEffect(amount=10, source=flame)
    esper.add_component(flame, dmg_effect)
    return flame


def goblin(pos: cmp.Position) -> int:
    """throws bombs"""
    cmps = []
    cmps.append(pos)
    cmps.append(cmp.Visible(glyph=dis.Glyph.GOBLIN, color=dis.Color.DARK_GREEN))
    cmps.append(cmp.Health(max=20))
    cmps.append(cmp.KnownAs(name="goblin"))
    cmps.append(cmp.Cooldown(turns=2))
    cmps.append(cmp.Enemy(perception=5, evaluate=behavior.goblin))
    cmps.append(cmp.Blocking())
    goblin = esper.create_entity(*cmps)

    dmg_effect = cmp.DamageEffect(amount=10, source=goblin)
    esper.add_component(goblin, dmg_effect)
    return goblin


def cyclops(pos: cmp.Position) -> int:
    cmps = []
    cmps.append(pos)
    cmps.append(cmp.Visible(glyph=dis.Glyph.CYCLOPS, color=dis.Color.CHOCOLATE))
    cmps.append(cmp.Health(max=20))
    cmps.append(cmp.KnownAs(name="cyclops"))

    cmps.append(cmp.Enemy(perception=4, evaluate=behavior.cyclops))
    cmps.append(cmp.Blocking())
    cyclops = esper.create_entity(*cmps)

    dmg_effect = cmp.DamageEffect(amount=10, source=cyclops)
    esper.add_component(cyclops, dmg_effect)
    return cyclops
