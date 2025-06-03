import collections
import textwrap
from dataclasses import dataclass

import esper

import components as cmp
import condition
import display
import ecs
import location
import typ

# an event is somethig that happens
# an action is somthing someone did
# event conflicts with input events, and they do overlap
# am I okay with calling something an action if it doesn't have a sentient origin?


class Log:
    """Messages to be displayed in in-game log"""

    messages: list = []
    log_len = display.PANEL_HEIGHT - 2

    @classmethod
    def append(cls, text: str):
        print(text)
        for line in textwrap.wrap(text, display.PANEL_WIDTH - 2):
            cls.messages.append(line)

        cls.messages = cls.messages[-cls.log_len :]
        esper.dispatch_event("redraw")


class Queues:
    """global queues that help one processor delegate an action to another"""

    movement = collections.deque()
    damage = collections.deque()
    tick = collections.deque()


class Event:
    _queue: collections.deque

    def __post_init__(self):
        self._queue.append(self)


@dataclass
class Damage(Event):
    _queue = Queues.damage
    source: int
    target: int
    amount: int


@dataclass
class Movement(Event):
    _queue = Queues.movement
    source: int
    x: int
    y: int


@dataclass
class Tick(Event):
    """A tick event is used to explicity track turns, for upkeeps"""

    _queue = Queues.tick


def collect_all_affected_entities(target: int) -> list[int]:
    try:
        targeting_ent = ecs.Query(cmp.Targeting).first()
    except KeyError:
        return [target]
    pos = esper.component_for_entity(target, cmp.Position)
    if not esper.has_component(targeting_ent, cmp.EffectArea):
        entities = [e for e in location.BOARD.entities[pos.x][pos.y]]
        return entities
    aoe = esper.component_for_entity(targeting_ent, cmp.EffectArea)

    entities = []

    for x, y in location.coords_within_radius(pos, aoe.radius):
        entities += [e for e in location.BOARD.entities[x][y]]
    return entities


def effects_to_events(source: int):
    """read effects off an entity and apply them to crosshair if needed"""
    # technically, every event can be callbackevent. for dmg, some standard dmg function can be used. would I want to refactor things to make that true?
    # it would break this function up

    if callback_cmp := esper.try_component(source, cmp.CallbackEffect):
        callback_cmp.callback()
        # the source doesn't exist once we new level. return early for now
        return

    if learnable := esper.try_component(source, cmp.Learnable):
        known_spells = esper.get_component(cmp.Known)
        if len(known_spells) == 4:
            Log.append("Max spells learned")
            raise typ.InvalidAction("learning failed")
        else:
            slotnum = min({1, 2, 3, 4} - {k[1].slot for k in known_spells})
            esper.add_component(learnable.spell, cmp.Known(slotnum))

    if cd_effect := esper.try_component(source, cmp.Cooldown):
        condition.grant(source, typ.Condition.Cooldown, cd_effect.turns)

    if not (target_cmp := esper.try_component(source, cmp.Target)):
        print(f"no target on effect holder {source}")
        return

    target = target_cmp.target
    if heal_effect := esper.try_component(source, cmp.HealEffect):
        Damage(source, target, -1 * heal_effect.amount)

    if bleed_effect := esper.try_component(source, cmp.BleedEffect):
        if esper.has_component(target, cmp.Cell):
            pos = esper.component_for_entity(target, cmp.Position)
            entities = collect_all_affected_entities(target)
            for ent in entities:
                if esper.has_component(ent, cmp.Health):
                    condition.grant(ent, typ.Condition.Bleed, bleed_effect.value)
        else:
            condition.grant(target, typ.Condition.Bleed, bleed_effect.value)

    if dmg_effect := esper.try_component(source, cmp.DamageEffect):
        if esper.has_component(target, cmp.Cell):
            pos = esper.component_for_entity(target, cmp.Position)
            entities = collect_all_affected_entities(target)
            for ent in entities:
                if esper.has_component(ent, cmp.Health):
                    Damage(dmg_effect.source, ent, dmg_effect.amount)
        else:
            Damage(dmg_effect.source, target, dmg_effect.amount)

    player_pos = ecs.Query(cmp.Player, cmp.Position).cmp(cmp.Position)
    if move_effect := esper.try_component(source, cmp.MoveEffect):
        pos = ecs.Query(cmp.Crosshair, cmp.Position).cmp(cmp.Position)
        x = pos.x - player_pos.x
        y = pos.y - player_pos.y
        Movement(move_effect.target, x, y)

    # note that removing Target is bad if persistent entity with static target
    esper.remove_component(source, cmp.Target)
