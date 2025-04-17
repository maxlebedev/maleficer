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
        cmp_db = esper._components
        self.include = include
        if cmp_sets := [cmp_db[cmp] for cmp in include if cmp in cmp_db]:
            self.entities = set.intersection(*cmp_sets)
        return self

    def exclude(self, *exclude):
        cmp_db = esper._components
        exclude = [cmp for cmp in exclude if cmp in cmp_db]
        if self.entities:
            [self.entities.difference_update(cmp_db[cmp]) for cmp in exclude]
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
