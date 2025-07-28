# ECS funcs to extend esper
from collections.abc import Generator

import esper

cmps = esper._entities


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

    def __iter__(self, *include) -> Generator[tuple[int, list]]:
        return self._get(*include)

    def _get(self, *include) -> Generator[tuple[int, list]]:
        entity_db = esper._entities
        if not self.entities or not self.include:
            return
        if not include:
            include = self.include
        cmp_set = set(include)
        for entity in self.entities:
            if cmp_set.issubset(entity_db[entity].keys()):
                yield entity, [entity_db[entity][cmp] for cmp in include]

    def first(self) -> int:
        """get the first entity in the queryset"""
        if self.entities:
            for entity in self.entities:
                return entity
        raise KeyError

    def cmp(self, cmp):
        """Get a given component of the (only) entity in the queryset"""
        if not self.entities or len(self.entities) != 1:
            raise KeyError
        for entity in self.entities:
            return cmps[entity][cmp]
        raise KeyError

    def remove(self, entities):
        if self.entities:
            self.entities.difference_update(entities)
        return self


def freeze_entity(source: int):
    """save an entity to a type:component dict"""
    components = esper.components_for_entity(source)
    ret = {type(cmp): cmp for cmp in components}
    return ret
