# game loops
import copy
import enum

import esper

import components as cmp
import create
import processors

ALL = dict()
CURRENT = None


class Ontology(enum.Enum):
    main_menu = enum.auto()
    options = enum.auto()
    about = enum.auto()
    level = enum.auto()
    target = enum.auto()
    inventory = enum.auto()
    char_select = enum.auto()


def main_menu_phase(context, console):
    background = "assets/main_menu.xp"
    title = "WELCOME TO MALEFICER"
    args = {"menu_cmp": cmp.MainMenu, "background": background, "title": title}
    render = processors.MenuRender(context, console, **args)
    input = processors.MenuInputEvent(cmp.MainMenu)

    ALL[Ontology.main_menu] = [render, input]
    create.ui.main_menu_opts()


def level_phase(context, console):
    upkeep = processors.Upkeep()

    render = processors.BoardRender(context, console)
    input = processors.GameInputEvent()
    npc = processors.NPCTurn()

    player_movement = processors.Movement()
    movement = processors.Movement()
    player_dmg = processors.Damage()
    npc_dmg = processors.Damage()
    death = processors.Death()

    level_procs = [
        upkeep,
        render,
        input,
        player_dmg,
        player_movement,
        npc,
        movement,
        npc_dmg,
        death,
    ]
    ALL[Ontology.level] = level_procs


def targeting_phase(context, console):
    position_cmp = cmp.Position(x=0, y=0)
    esper.create_entity(cmp.Crosshair(), position_cmp)

    input = processors.TargetInputEvent()
    target_render = processors.TargetRender(context, console)
    movement = processors.Movement()
    ALL[Ontology.target] = [target_render, input, movement]


def inventory_phase(context, console):
    esper.create_entity(cmp.MenuSelection())

    input = processors.InventoryInputEvent()
    render = processors.InventoryRender(context, console)

    ALL[Ontology.inventory] = [render, input]


def options_phase(context, console):
    render = processors.OptionsRender(context, console)
    input = processors.OptionsInputEvent()

    ALL[Ontology.options] = [render, input]


def about_phase(context, console):
    render = processors.AboutRender(context, console)
    input = processors.AboutInputEvent()

    ALL[Ontology.about] = [render, input]


def char_select_phase(context, console):
    background = "assets/char_select.xp"
    title = "Select a Character"
    args = {"menu_cmp": cmp.StartMenu, "background": background, "title": title}
    render = processors.MenuRender(context, console, **args)
    input = processors.MenuInputEvent(cmp.StartMenu)

    ALL[Ontology.char_select] = [render, input]
    create.ui.char_select_opts()


def change_to(phase: Ontology, start_proc: type[esper.Processor] | None = None):
    """We dynamically add and remove processors when moving between phases. Each phase has its own proc loop."""
    global CURRENT
    for proc in esper._processors:
        esper.remove_processor(type(proc))
    esper._processors = []

    proc_list = copy.copy(ALL[phase])  # copy to prevent mutation of original
    if start_proc:
        while start_proc and not isinstance(proc_list[0], start_proc):
            proc_list.append(proc_list.pop(0))

    tot_procs = len(proc_list)
    for i, proc in enumerate(proc_list):
        esper.add_processor(proc, priority=tot_procs - i)
    CURRENT = phase


def oneshot(proctype: type[esper.Processor]):
    """only works on processors that are already registered"""
    if proc_instance := esper.get_processor(proctype):
        proc_instance.process()


def setup(context, console):
    main_menu_phase(context, console)
    level_phase(context, console)
    targeting_phase(context, console)
    inventory_phase(context, console)
    options_phase(context, console)
    about_phase(context, console)
    char_select_phase(context, console)
