import collections
import esper

import components as cmp
from . import item
import display as dis


def inventory_map() -> list:
    inventory = esper.get_components(cmp.InInventory, cmp.Onymous)
    inventory_map = collections.defaultdict(set)
    for entity, (_, named) in inventory:
        inventory_map[named.name].add(entity)
    # TODO: create a cmp.MenuItem on collection, then set the order in this func
    # then display is just a matter of lookup
    sorted_map = sorted(inventory_map.items())
    return sorted_map


def alamar():
    """default player character"""
    cmps = []
    cmps.append(cmp.Player())
    cmps.append(cmp.Visible(glyph=dis.Glyph.PLAYER, color=dis.Color.GREEN))
    cmps.append(cmp.Position(x=1, y=1))
    cmps.append(cmp.Health(max=10))
    cmps.append(cmp.Onymous(name="player"))
    cmps.append(cmp.Blocking())
    cmps.append(cmp.LastPosition(cmp.Position(x=1, y=1)))
    esper.create_entity(*cmps)


def starting_inventory():
    starting_potion = item.potion()
    esper.add_component(starting_potion, cmp.InInventory())
