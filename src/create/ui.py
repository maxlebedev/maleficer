import esper

import components as cmp
import create
import ecs
import location
import phase


def initial_map():
    board = location.get_board()
    # location.generate_test_dungeon(board)
    # location.generate_dungeon(board)
    # location.cave_dungeon(board)
    location.maze_dungeon(board)
    board.build_entity_cache()


def start_game():
    initial_map()
    create.player.starting_inventory()

    game_meta = ecs.Query(cmp.GameMeta).val
    game_meta.level = 1

    order0 = lambda x: x.order == 0
    all_main_menu_opts = ecs.Query(cmp.MainMenu, cmp.MenuItem)
    first_main_menu_opt = all_main_menu_opts.where(cmp.MenuItem, order0).first()
    esper.delete_entity(first_main_menu_opt, True)

    callback = lambda _: phase.change_to(phase.Ontology.level)
    _make_menuitem(cmp.MainMenu, callback, "Continue", 0)


def _make_menuitem(menu_cmp, callback, name, order):
    cmps = []
    cmps.append(menu_cmp())
    cmps.append(cmp.Onymous(name=name))
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


def char_select_opts():
    # TODO: these can probably be consolidated, maybe even into some startgame()
    def pick_alamar(_):
        create.player.alamar()
        start_game()
        phase.change_to(phase.Ontology.level)

    def pick_beatrice(_):
        create.player.beatrice()
        start_game()
        phase.change_to(phase.Ontology.level)

    _make_menuitem(cmp.StartMenu, pick_alamar, "Alamar (80/blink/firebolt)", 0)
    _make_menuitem(cmp.StartMenu, pick_beatrice, "Beatrice (100/daze/mulilate)", 1)
