import esper

import components as cmp
import create
import ecs
import location
import phase


def start_game():
    location.new_map()
    create.player.starting_inventory()

    order0 = lambda x: x.order == 0
    all_main_menu_opts = ecs.Query(cmp.MainMenu, cmp.MenuItem)
    first_main_menu_opt = all_main_menu_opts.where(cmp.MenuItem, order0).first()
    esper.delete_entity(first_main_menu_opt, True)

    callback = lambda _: phase.change_to(phase.Ontology.level)
    _make_menuitem(cmp.MainMenu, callback, "Continue", 0)


def _make_menuitem(menu_cmp, callback, name, order):
    cmps = []
    cmps.append(menu_cmp())
    cmps.append(cmp.KnownAs(name=name))
    cmps.append(cmp.MenuItem(order=order))
    cmps.append(cmp.UseTrigger(callbacks=[callback]))
    esper.create_entity(*cmps)


def main_menu_opts():
    callback = lambda _: phase.change_to(phase.Ontology.char_select)
    _make_menuitem(cmp.MainMenu, callback, "Start Game", 0)
    callback = lambda _: phase.change_to(phase.Ontology.options)
    _make_menuitem(cmp.MainMenu, callback, "Options", 1)
    callback = lambda _: phase.change_to(phase.Ontology.about)
    _make_menuitem(cmp.MainMenu, callback, "About", 2)

    def exit(_):
        raise SystemExit()

    _make_menuitem(cmp.MainMenu, exit, "Quit", 3)


def discipline_opts():
    # TODO: does this wanna live here?
    # can we generate the desc string?

    def make_picker(create_player):
        def picker(_):
            create_player()
            start_game()
            phase.change_to(phase.Ontology.level)

        return picker

    pick_adept = make_picker(create.player.adept)
    pick_bloodmage = make_picker(create.player.bloodmage)
    pick_terramancer = make_picker(create.player.terramancer)
    pick_stormcaller = make_picker(create.player.stormcaller)

    opts = [
        (pick_adept, "Adept (80hp/blink/firebolt)"),
        (pick_bloodmage, "Bloodmage (100hp/daze/mutilate)"),
        (pick_terramancer, "Terramancer (100hp/crush/pull)"),
        (pick_stormcaller, "Stormcaller (70hp/lighning/blink)"),
    ]

    for i, (func, desc) in enumerate(opts):
        _make_menuitem(cmp.StartMenu, func, desc, i)
