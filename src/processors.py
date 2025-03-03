import esper
import components as cmp
import actions
import tcod
from functools import partial

# TODO: more things need to be here
class MovementProcessor(esper.Processor):
    def process(self):
        for ent, (move, pos) in esper.get_components(cmp.Movement, cmp.Position):
            pos.x += move.x
            pos.y += move.y
            esper.remove_component(ent, cmp.Movement)

# TODO: redundant with event handler?
class EventProcessor(esper.Processor):

    def __init__(self, event_handler):
        self.event_handler = event_handler

    def process(self):
        player, _ = esper.get_component(cmp.Player)[0]
        for event in tcod.event.wait():
            action = self.event_handler.dispatch(event)
            if action and isinstance(action, actions.MovementAction):
                esper.add_component(player, cmp.Movement(x=action.dx, y=action.dy))


class RenderProcessor(esper.Processor):
    def __init__(self, engine, console, context):
        self.render_func = partial(engine.render, console, context)

    def process(self):
        self.render_func()
