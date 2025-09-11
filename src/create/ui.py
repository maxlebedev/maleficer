import phase
import components as cmp
import esper


def main_menu_opts():
    def make_menuitem(aphase, name, order):
        callback = lambda _: phase.change_to(aphase)
        cmps = []
        cmps.append(cmp.MainMenu())
        cmps.append(cmp.Onymous(name=name))
        cmps.append(cmp.MenuItem(order=order))
        cmps.append(cmp.UseTrigger(callbacks=[callback]))
        esper.create_entity(*cmps)

    make_menuitem(phase.Ontology.level, "Start Game", 0)
    make_menuitem(phase.Ontology.options, "Options", 1)
    make_menuitem(phase.Ontology.about, "About", 2)


def phases(context, console):
    phase.main_menu_phase(context, console)
    phase.level_phase(context, console)
    phase.targeting_phase(context, console)
    phase.inventory_phase(context, console)
    phase.options_phase(context, console)
    phase.about_phase(context, console)
