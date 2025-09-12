import random

import esper

import components as cmp
import create
import location
import phase


def initial_map():
    # location.generate_test_dungeon(location.BOARD)
    location.generate_dungeon(location.BOARD)
    # location.cave_dungeon(location.BOARD)
    # location.maze_dungeon(location.BOARD)
    location.BOARD.build_entity_cache()


def start_game():
    initial_map()
    starting_spells = [
        create.spell.firebolt,
        create.spell.blink,
        create.spell.bleed,
    ]

    spells = random.sample(starting_spells, 2)
    for spell in spells:
        spell()

    create.player.starting_inventory()
    location.LEVEL = 1
    phase.change_to(phase.Ontology.start)


def to_level(_):
    if location.LEVEL == 0:
        start_game()
    else:
        phase.change_to(phase.Ontology.level)


def main_menu_opts():
    def make_menuitem(callback, name, order):
        cmps = []
        cmps.append(cmp.MainMenu())
        cmps.append(cmp.Onymous(name=name))
        cmps.append(cmp.MenuItem(order=order))
        cmps.append(cmp.UseTrigger(callbacks=[callback]))
        esper.create_entity(*cmps)

    make_menuitem(to_level, "Start Game", 0)
    callback = lambda _: phase.change_to(phase.Ontology.options)
    make_menuitem(callback, "Options", 1)
    callback = lambda _: phase.change_to(phase.Ontology.about)
    make_menuitem(callback, "About", 2)


def start_opts():
    def make_menuitem(callback, name, order):
        cmps = []
        cmps.append(cmp.StartMenu())
        cmps.append(cmp.Onymous(name=name))
        cmps.append(cmp.MenuItem(order=order))
        cmps.append(cmp.UseTrigger(callbacks=[callback]))
        esper.create_entity(*cmps)

    callback = lambda _: phase.change_to(phase.Ontology.level)
    make_menuitem(callback, "Start", 0)


def phases(context, console):
    phase.main_menu_phase(context, console)
    phase.level_phase(context, console)
    phase.targeting_phase(context, console)
    phase.inventory_phase(context, console)
    phase.options_phase(context, console)
    phase.about_phase(context, console)
    phase.start_phase(context, console)
