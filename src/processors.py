import esper
import components as cmp

class MovementProcessor(esper.Processor):
    def process(self):
        for ent, (move, pos) in esper.get_components(cmp.Movement, cmp.Position):
            pos.x += move.x
            pos.y += move.y
            esper.remove_component(ent, cmp.Movement)
