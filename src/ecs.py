# ECS funcs to extend esper
from collections.abc import Generator


import esper

class Query:
    entities = None
    include = tuple()

    def __init__(self, *include):
        if include:
            self.filter(*include)

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

    def get(self, *include) -> Generator[tuple[int, list]]:
        entity_db = esper._entities
        if not self.entities or not self.include:
            return
        if not include:
            include = self.include

        for entity in self.entities:
            yield entity, [entity_db[entity][cmp] for cmp in include]


    def first(self, *include):
        return next(self.get(*include))

    def first_cmp(self, *include):
        """get only the components of the first entity"""
        components = next(self.get(*include))[1]
        for component in components:
            yield component
