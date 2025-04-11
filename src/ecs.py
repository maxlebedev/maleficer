# ECS funcs to extend esper
import esper


class Query:
    entities = None
    include = None

    def filter(self, *include):
        comp_db = esper._components
        self.include = include
        self.entities = set.intersection(*[comp_db[ct] for ct in include])
        return self

    def exclude(self, *exclude):
        comp_db = esper._components
        if self.entities:
            [self.entities.difference_update(comp_db[ct]) for ct in exclude]
        return self

    def get(self):
        entity_db = esper._entities
        if self.entities and self.include:
            for entity in self.entities:
                yield entity, [entity_db[entity][cmp] for cmp in self.include]
