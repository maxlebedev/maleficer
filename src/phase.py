# game loops
import enum

import esper

import components as cmp
import create
import processors
import ecs

ALL = dict()


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
    enqueue = processors.Enqueue(_phase=Ontology.main_menu)

    ALL[Ontology.main_menu] = [render, input, enqueue]
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
    enqueue = processors.Enqueue(_phase=Ontology.level)

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
        enqueue,
    ]
    ALL[Ontology.level] = level_procs


def targeting_phase(context, console):
    position_cmp = cmp.Position(x=0, y=0)
    esper.create_entity(cmp.Crosshair(), position_cmp)

    input = processors.TargetInputEvent()
    target_render = processors.TargetRender(context, console)
    movement = processors.Movement()
    enqueue = processors.Enqueue(_phase=Ontology.target)
    ALL[Ontology.target] = [target_render, input, movement, enqueue]


def inventory_phase(context, console):
    esper.create_entity(cmp.MenuSelection())

    input = processors.InventoryInputEvent()
    render = processors.InventoryRender(context, console)
    enqueue = processors.Enqueue(_phase=Ontology.inventory)

    ALL[Ontology.inventory] = [render, input, enqueue]


def options_phase(context, console):
    render = processors.OptionsRender(context, console)
    input = processors.OptionsInputEvent()
    enqueue = processors.Enqueue(_phase=Ontology.options)

    ALL[Ontology.options] = [render, input, enqueue]


def about_phase(context, console):
    render = processors.AboutRender(context, console)
    input = processors.AboutInputEvent()
    enqueue = processors.Enqueue(_phase=Ontology.about)

    ALL[Ontology.about] = [render, input, enqueue]


def char_select_phase(context, console):
    background = "assets/char_select.xp"
    title = "Select a Character"
    args = {"menu_cmp": cmp.StartMenu, "background": background, "title": title}
    render = processors.MenuRender(context, console, **args)
    input = processors.MenuInputEvent(cmp.StartMenu)

    enqueue = processors.Enqueue(_phase=Ontology.char_select)

    ALL[Ontology.char_select] = [render, input, enqueue]
    create.ui.char_select_opts()


def change_to(next_phase: Ontology, start_proc: type[esper.Processor] | None = None):
    processors.PROC_QUEUE.clear()
    processors.PROC_QUEUE.append(ALL[next_phase][-1])

    game_meta = ecs.Query(cmp.GameMeta).val
    if not game_meta.process:
        game_meta.process = ALL[next_phase][-1]

    if start_proc:
        ALL[next_phase][-1]._process()
        while not isinstance(processors.PROC_QUEUE[0], start_proc):
            processors.PROC_QUEUE.popleft()


def oneshot(proctype: type[esper.Processor]):
    """immidiately run the process, since we are still in another proc"""
    if proc_instance := esper.get_processor(proctype):
        proc_instance._process()


def setup(context, console):
    main_menu_phase(context, console)
    level_phase(context, console)
    targeting_phase(context, console)
    inventory_phase(context, console)
    options_phase(context, console)
    about_phase(context, console)
    char_select_phase(context, console)

    animation = processors.Animation(context, console)
    esper.add_processor(animation)

    for procs in ALL.values():
        for proc in procs:
            esper.add_processor(proc)
