import collections

import esper

import behavior
import components as cmp
import display as dis

from . import item, spell


def inventory_map() -> list:
    inventory = esper.get_components(cmp.InInventory, cmp.Onymous)
    inventory_map = collections.defaultdict(set)
    for entity, (_, named) in inventory:
        inventory_map[named.name].add(entity)
    # TODO: create a cmp.MenuItem on collection, then set the order in this func
    # then display is just a matter of lookup
    sorted_map = sorted(inventory_map.items())
    return sorted_map


def adept():
    cmps = []
    cmps.append(cmp.Player())
    cmps.append(cmp.Visible(glyph=dis.Glyph.PLAYER, color=dis.Color.GREEN))
    cmps.append(cmp.Position(x=1, y=1))
    cmps.append(cmp.Health(max=80))
    cmps.append(cmp.Onymous(name="player"))
    cmps.append(cmp.Blocking())
    cmps.append(cmp.LastPosition(cmp.Position(x=1, y=1)))
    esper.create_entity(*cmps)

    behavior._learn(spell.firebolt())
    behavior._learn(spell.blink())


def bloodmage():
    cmps = []
    cmps.append(cmp.Player())
    cmps.append(cmp.Visible(glyph=dis.Glyph.PLAYER, color=dis.Color.RED))
    cmps.append(cmp.Position(x=1, y=1))
    cmps.append(cmp.Health(max=100))
    cmps.append(cmp.Onymous(name="player"))
    cmps.append(cmp.Blocking())
    cmps.append(cmp.LastPosition(cmp.Position(x=1, y=1)))
    esper.create_entity(*cmps)

    behavior._learn(spell.daze())
    behavior._learn(spell.lacerate())


def terramancer():
    cmps = []
    cmps.append(cmp.Player())
    cmps.append(cmp.Visible(glyph=dis.Glyph.PLAYER, color=dis.Color.BROWN))
    cmps.append(cmp.Position(x=1, y=1))
    cmps.append(cmp.Health(max=100))
    cmps.append(cmp.Onymous(name="player"))
    cmps.append(cmp.Blocking())
    cmps.append(cmp.LastPosition(cmp.Position(x=1, y=1)))
    esper.create_entity(*cmps)

    behavior._learn(spell.pull())
    behavior._learn(spell.crush())

def stormcaller():
    cmps = []
    cmps.append(cmp.Player())
    cmps.append(cmp.Visible(glyph=dis.Glyph.PLAYER, color=dis.Color.YELLOW))
    cmps.append(cmp.Position(x=1, y=1))
    cmps.append(cmp.Health(max=70))
    cmps.append(cmp.Onymous(name="player"))
    cmps.append(cmp.Blocking())
    cmps.append(cmp.LastPosition(cmp.Position(x=1, y=1)))
    esper.create_entity(*cmps)

    behavior._learn(spell.blink())
    behavior._learn(spell.lighting())


def starting_inventory():
    starting_potion = item.potion()
    esper.add_component(starting_potion, cmp.InInventory())
