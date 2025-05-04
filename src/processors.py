import copy
import itertools
import random
from dataclasses import dataclass

import esper
import tcod
from tcod import libtcodpy
from tcod.map import compute_fov

import components as cmp
import condition
import create
import display
import ecs
import event
import input
import location
import scene
import typ
import math_util


@dataclass
class Movement(esper.Processor):
    def bump(self, source, target):
        """one entity bumps into another"""
        src_is_enemy = esper.has_component(source, cmp.Enemy)
        target_is_harmable = esper.has_component(target, cmp.Health)
        if src_is_enemy and target_is_harmable:
            esper.add_component(source, cmp.Target(target=target))
            event.effects_to_events(source)

        if esper.has_component(source, cmp.Player):
            # Note: walking into a wall consumes a turn
            event.Log.append("Failed to move to invalid location")
            esper.dispatch_event("flash")

    def collect(self, target):
        location.BOARD.remove(target)
        esper.add_component(target, cmp.InInventory())
        create.inventory_map()
        name = esper.component_for_entity(target, cmp.Onymous).name
        event.Log.append(f"player picked up {name}")
        # oneshot call some collectable processor?

    def process(self):
        board = location.BOARD
        while event.Queues.movement:
            movement = event.Queues.movement.popleft()  # left so player first
            ent = movement.source
            if not esper.entity_exists(ent):
                # entity intends to move, but dies first
                continue

            ent_is_player = esper.has_component(ent, cmp.Player)
            ent_has_hp = esper.has_component(ent, cmp.Health)
            pos = esper.component_for_entity(ent, cmp.Position)
            new_x = pos.x + movement.x
            new_y = pos.y + movement.y
            targets = copy.copy(board.entities[new_x][new_y])

            move = True
            if ent_has_hp:
                blockers = esper._components[cmp.Blocking]
                move = not any(target in blockers for target in targets)

            if move:
                board.reposition(ent, new_x, new_y)

            if ent_has_hp:
                for target in targets:
                    is_target = lambda x: esper.has_component(target, x)

                    if is_target(cmp.Blocking):
                        self.bump(ent, target)

                    if ent_is_player and is_target(cmp.Collectable):
                        self.collect(target)

                    ent_flies = esper.has_component(ent, cmp.Flying)
                    if not ent_flies and is_target(cmp.Trap):
                        if esper.has_component(target, cmp.DamageEffect):
                            esper.add_component(target, cmp.Target(target=ent))
                        event.effects_to_events(target)


@dataclass
class Damage(esper.Processor):
    def process(self):
        while event.Queues.damage:
            damage = event.Queues.damage.popleft()
            if not all(map(esper.entity_exists, [damage.target, damage.source])):
                # if either entity doesn't exist anymore, damage fizzles
                continue

            math_util.apply_damage(damage.target, damage.amount)

            to_name = lambda x: esper.component_for_entity(x, cmp.Onymous).name
            src_name = to_name(damage.source)
            target_name = to_name(damage.target)

            message = f"{src_name} heals {-1 * damage.amount} to {target_name}"
            if damage.amount > 0:
                message = f"{src_name} deals {damage.amount} to {target_name}"
            event.Log.append(message)


@dataclass
class Death(esper.Processor):
    def process(self):
        # crashes if player gets deleted
        for killable, (health, named) in ecs.Query(cmp.Health, cmp.Onymous):
            if health.current <= 0:
                message = f"{named.name} is no more"
                event.Log.append(message)
                location.BOARD.remove(killable)
                esper.delete_entity(killable, immediate=True)


@dataclass
class InputEvent(esper.Processor):
    action_map = {}

    def exit(self):
        raise SystemExit()

    def process(self):
        listen = True
        while listen:
            for input_event in tcod.event.wait():
                # if we ever have other events we care abt, we can dispatch by type
                if not isinstance(input_event, tcod.event.KeyDown):
                    continue
                if input_event.sym in self.action_map:
                    try:
                        match self.action_map[input_event.sym]:
                            case (func, args):
                                func(*args)
                            case func:
                                func()
                    except typ.InvalidAction as e:
                        esper.dispatch_event("flash")
                        event.Log.append(str(e))
                    else:
                        listen = False


@dataclass
class GameInputEvent(InputEvent):
    def __init__(self):
        self.action_map = {
            input.KEYMAP[input.Input.MOVE_DOWN]: (self.move, [0, 1]),
            input.KEYMAP[input.Input.MOVE_LEFT]: (self.move, [-1, 0]),
            input.KEYMAP[input.Input.MOVE_UP]: (self.move, [0, -1]),
            input.KEYMAP[input.Input.MOVE_RIGHT]: (self.move, [1, 0]),
            input.KEYMAP[input.Input.ESC]: (scene.to_phase, [scene.Phase.menu]),
            input.KEYMAP[input.Input.ONE]: (self.to_target, [1]),
            input.KEYMAP[input.Input.TWO]: (self.to_target, [2]),
            input.KEYMAP[input.Input.THREE]: (self.to_target, [3]),
            input.KEYMAP[input.Input.FOUR]: (self.to_target, [4]),
            input.KEYMAP[input.Input.TAB]: self.to_inventory,
            input.KEYMAP[input.Input.SKIP]: self.skip,
        }

    def to_inventory(self):
        try:
            ecs.Query(cmp.InInventory).first()
        except KeyError:
            raise typ.InvalidAction

        menu_selection = ecs.Query(cmp.MenuSelection).cmp(cmp.MenuSelection)
        menu_selection.item = 0
        scene.to_phase(scene.Phase.inventory)

    def skip(self):
        event.Tick()

    def move(self, x, y):
        player = ecs.Query(cmp.Player).first()
        event.Movement(player, x, y)
        event.Tick()

    def to_target(self, slot: int):
        # TODO: This probably wants to take spell_ent and not slot num
        casting_spell = None
        for spell_ent, (known) in esper.get_component(cmp.Known):
            if known.slot == slot:
                casting_spell = spell_ent

        if not casting_spell:
            raise typ.InvalidAction("spell doesn't exist")
        if condition.has(casting_spell, typ.Condition.Cooldown):
            raise typ.InvalidAction("spell on cooldown")

        player_pos = location.player_position()
        xhair_ent = ecs.Query(cmp.Crosshair, cmp.Position).first()
        location.BOARD.reposition(xhair_ent, *player_pos)
        esper.add_component(casting_spell, cmp.Targeting())
        scene.to_phase(scene.Phase.target)


@dataclass
class NPCTurn(esper.Processor):
    def wander(self, entity: int):
        dir = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0), (0, 0)])
        if dir == (0, 0):
            return
        event.Movement(entity, *dir)

    def pathfind(self, entity_pos, end_pos):
        cost = location.BOARD.as_move_graph()
        graph = tcod.path.SimpleGraph(cost=cost, cardinal=1, diagonal=0)
        pf = tcod.path.Pathfinder(graph)
        pf.add_root(entity_pos.as_tuple)
        path: list = pf.path_to(end_pos.as_tuple).tolist()
        if len(path) < 2:
            return (0, 0)
        return path[1]

    def process(self):
        for entity, _ in esper.get_component(cmp.Wander):
            self.wander(entity)

        player_pos = location.player_position()
        for entity, (melee, epos) in ecs.Query(cmp.Melee, cmp.Position):
            dist_to_player = location.euclidean_distance(player_pos, epos)
            if dist_to_player > melee.radius:
                self.wander(entity)
            else:
                x, y = self.pathfind(epos, player_pos)
                event.Movement(entity, x=x - epos.x, y=y - epos.y)


@dataclass
class Render(esper.Processor):
    console: tcod.console.Console
    context: tcod.context.Context

    def render_bar(self, x: int, y: int, curr: int, maximum: int, total_width: int):
        bar_width = int(curr / maximum * total_width)
        bg = display.Color.BAR_EMPTY
        self.console.draw_rect(x=x, y=y, width=total_width, height=1, ch=1, bg=bg)

        if bar_width > 0:
            bg = display.Color.BAR_FILLED
            self.console.draw_rect(x=x, y=y, width=bar_width, height=1, ch=1, bg=bg)

        text = f"HP: {curr}/{maximum}"
        self.console.print(x=x, y=y, string=text, fg=display.Color.DGREY)

    def _draw_panels(self):
        panel_params = {
            "y": 0,
            "width": display.PANEL_WIDTH,
            "height": display.PANEL_HEIGHT,
            "decoration": (
                display.Glyph.FRAME1,
                display.Glyph.FRAME2,
                display.Glyph.FRAME3,
                display.Glyph.FRAME4,
                display.Glyph.NONE,
                display.Glyph.FRAME6,
                display.Glyph.FRAME7,
                display.Glyph.FRAME8,
                display.Glyph.FRAME9,
            ),
        }
        dashes = "-" * (display.PANEL_WIDTH - 2)

        # left panel
        self.console.draw_frame(x=0, **panel_params)
        hp = ecs.Query(cmp.Player, cmp.Health).cmp(cmp.Health)
        self.render_bar(1, 1, hp.current, hp.max, display.PANEL_WIDTH - 2)

        # inventory
        inv_map = create.inventory_map()
        for i, (name, entities) in enumerate(inv_map):
            self.console.print(1, 3 + i, f"{len(entities)}x {name}")

        # spells
        self.console.print(1, 8, dashes)
        spells = ecs.Query(cmp.Spell, cmp.Onymous, cmp.Known)
        sorted_spells = sorted(spells, key=lambda x: x[1][2].slot)
        for i, (spell_ent, (_, named, known)) in enumerate(sorted_spells):
            # TODO: 9 is arbitrary
            text = f"Slot{known.slot}:{named.name}"
            if cd := condition.get_val(spell_ent, typ.Condition.Cooldown):
                text = f"{text}:{typ.Condition.Cooldown.name} {cd}"
            self.console.print(1, 9 + i, text)

        # if targeting, also print spell info
        targeting = esper.get_component(cmp.Targeting)
        if targeting:
            trg_ent, _ = targeting[0]
            y_idx = itertools.count(12)
            self.console.print(1, next(y_idx), dashes)
            spell_component_details = [
                ("Damage", cmp.DamageEffect, "amount"),
                ("Range", cmp.Spell, "target_range"),
                ("Cooldown", cmp.Cooldown, "turns"),
            ]
            for name, try_cmp, attr in spell_component_details:
                component = esper.try_component(trg_ent, try_cmp)
                if component:
                    value = getattr(component, attr)
                    self.console.print(1, next(y_idx), f"{name}:{value}")
            if bleed_effect := esper.try_component(trg_ent, cmp.BleedEffect):
                message = f"Grants Bleed:{bleed_effect.value}"
                self.console.print(1, next(y_idx), message)

        # right panel
        self.console.draw_frame(x=display.R_PANEL_START, **panel_params)
        for i, message in enumerate(event.Log.messages):
            self.console.print(1 + display.R_PANEL_START, 1 + i, message)

    def _apply_lighting(self, cell_rgbs, in_fov) -> list[list[typ.CELL_RGB]]:
        """display cells in fov with lighting, explored without, and hide the rest"""
        for x, col in enumerate(cell_rgbs):
            for y, (glyph, fgcolor, _) in enumerate(col):
                cell = location.BOARD.get_cell(x, y)
                if not cell:
                    continue
                if in_fov[x][y]:
                    location.BOARD.explored.add(cell)
                    brighter = display.brighter(fgcolor, scale=100)
                    cell_rgbs[x][y] = (glyph, brighter, display.Color.CANDLE)
                elif cell in location.BOARD.explored:
                    cell_rgbs[x][y] = (glyph, fgcolor, display.Color.BLACK)
                else:
                    cell_rgbs[x][y] = (glyph, display.Color.BLACK, display.Color.BLACK)
        return cell_rgbs

    def _get_fov(self):
        transparency = location.BOARD.as_transparency()
        pos = location.player_position()
        algo = libtcodpy.FOV_SHADOW
        fov = compute_fov(transparency, pos.as_tuple, radius=4, algorithm=algo)
        return fov

    def present(self, cell_rgbs):
        startx, endx = (display.PANEL_WIDTH, display.R_PANEL_START)
        starty, endy = (0, display.BOARD_HEIGHT)
        self.console.rgb[startx:endx, starty:endy] = cell_rgbs
        self.context.present(self.console)  # , integer_scaling=True


@dataclass
class BoardRender(Render):
    console: tcod.console.Console
    context: tcod.context.Context

    def _get_cell_rgbs(self):
        board = location.BOARD
        cell_rgbs = [list(map(board.as_rgb, row)) for row in board.cells]

        in_fov = self._get_fov()

        nonwall_drawables = ecs.Query(cmp.Position, cmp.Visible).exclude(cmp.Cell)
        for _, (pos, vis) in nonwall_drawables.exclude(cmp.Blocking):
            if not in_fov[pos.x][pos.y]:
                continue
            cell_rgbs[pos.x][pos.y] = (vis.glyph, vis.color, vis.bg_color)

        foreground = nonwall_drawables.filter(cmp.Position, cmp.Visible, cmp.Blocking)
        for _, (pos, vis, _) in foreground:
            if not in_fov[pos.x][pos.y]:
                continue
            cell_rgbs[pos.x][pos.y] = (vis.glyph, vis.color, vis.bg_color)

        cell_rgbs = self._apply_lighting(cell_rgbs, in_fov)
        return cell_rgbs

    def process(self):
        self.console.clear()
        self._draw_panels()
        cell_rgbs = self._get_cell_rgbs()
        self.present(cell_rgbs)


@dataclass
class MenuRender(esper.Processor):
    context: tcod.context.Context
    console: tcod.console.Console

    def process(self):
        self.console.clear()
        x = display.PANEL_WIDTH + (display.BOARD_WIDTH // 2)
        y = display.BOARD_HEIGHT // 2
        self.console.print(x, y, "WELCOME TO MALEFICER", alignment=libtcodpy.CENTER)
        self.context.present(self.console)  # , integer_scaling=True


@dataclass
class MenuInputEvent(InputEvent):
    def __init__(self):
        self.action_map = {
            input.KEYMAP[input.Input.ESC]: self.exit,
            input.KEYMAP[input.Input.SELECT]: (scene.to_phase, [scene.Phase.level]),
        }


@dataclass
class TargetInputEvent(InputEvent):
    def __init__(self):
        self.action_map = {
            input.KEYMAP[input.Input.MOVE_DOWN]: (self.move_crosshair, [0, 1]),
            input.KEYMAP[input.Input.MOVE_LEFT]: (self.move_crosshair, [-1, 0]),
            input.KEYMAP[input.Input.MOVE_UP]: (self.move_crosshair, [0, -1]),
            input.KEYMAP[input.Input.MOVE_RIGHT]: (self.move_crosshair, [1, 0]),
            input.KEYMAP[input.Input.ESC]: self.to_level,
            input.KEYMAP[input.Input.SELECT]: self.select,
        }

    def to_level(self):
        spell_ent = ecs.Query(cmp.Targeting).first()
        esper.remove_component(spell_ent, cmp.Targeting)
        scene.to_phase(scene.Phase.level)

    def move_crosshair(self, x, y):
        crosshair = ecs.Query(cmp.Crosshair, cmp.Position).first()
        pos = ecs.cmps[crosshair][cmp.Position]

        # TODO: maybe break out range to its own cmp and check for it here
        spell_cmp = ecs.Query(cmp.Spell, cmp.Targeting).cmp(cmp.Spell)

        player_pos = location.player_position()
        new_pos = cmp.Position(pos.x + x, pos.y + y)
        dist_to_player = location.euclidean_distance(player_pos, new_pos)
        if not spell_cmp or dist_to_player < spell_cmp.target_range:
            event.Movement(crosshair, x, y)

    def select(self):
        xhair_pos = ecs.Query(cmp.Crosshair, cmp.Position).cmp(cmp.Position)
        targeting_entity = ecs.Query(cmp.Targeting).first()
        if not esper.has_component(targeting_entity, cmp.Target):
            cell = xhair_pos.lookup_in(location.BOARD.cells)
            trg = cmp.Target(target=cell)
            esper.add_component(targeting_entity, trg)

        event.effects_to_events(targeting_entity)
        esper.remove_component(targeting_entity, cmp.Targeting)
        event.Tick()
        scene.to_phase(scene.Phase.level, NPCTurn)


@dataclass
class TargetRender(BoardRender):
    console: tcod.console.Console
    context: tcod.context.Context

    def process(self) -> None:
        self.console.clear()
        self._draw_panels()

        cell_rgbs = self._get_cell_rgbs()

        drawable_areas = ecs.Query(cmp.Position, cmp.EffectArea)
        for _, (pos, aoe) in drawable_areas:
            cell = cell_rgbs[pos.x][pos.y]
            cell_rgbs[pos.x][pos.y] = cell[0], cell[1], aoe.color

        self.present(cell_rgbs)


@dataclass
class InventoryRender(BoardRender):
    console: tcod.console.Console
    context: tcod.context.Context

    def display_inventory(self):
        menu_selection = ecs.Query(cmp.MenuSelection).cmp(cmp.MenuSelection)

        inv_map = create.inventory_map()
        for i, (name, entities) in enumerate(inv_map):
            text = f"{len(entities)}x {name}"
            fg = display.Color.WHITE
            bg = display.Color.BLACK
            if menu_selection.item == i:
                fg, bg = bg, fg
            self.console.print(1, 3 + i, string=text, fg=fg, bg=bg)

    def process(self) -> None:
        self.console.clear()
        self._draw_panels()

        cell_rgbs = self._get_cell_rgbs()

        self.display_inventory()
        self.present(cell_rgbs)


@dataclass
class InventoryInputEvent(InputEvent):
    def __init__(self):
        to_level = (scene.to_phase, [scene.Phase.level])
        self.action_map = {
            input.KEYMAP[input.Input.MOVE_DOWN]: (self.move_selection, [1]),
            input.KEYMAP[input.Input.MOVE_UP]: (self.move_selection, [-1]),
            input.KEYMAP[input.Input.ESC]: to_level,
            input.KEYMAP[input.Input.SELECT]: self.use_item,
        }

    def move_selection(self, diff: int):
        menu_selection = ecs.Query(cmp.MenuSelection).cmp(cmp.MenuSelection)
        inventory_size = len(create.inventory_map()) - 1
        menu_selection.item += diff
        menu_selection.item = math_util.clamp(menu_selection.item, inventory_size)

    def use_item(self):
        inv_map = create.inventory_map()
        menu_selection = ecs.Query(cmp.MenuSelection).cmp(cmp.MenuSelection)
        name = inv_map[menu_selection.item][0]
        selection = inv_map[menu_selection.item][1].pop()
        print(f"using {name}: {selection}")

        event.effects_to_events(selection)

        esper.remove_component(selection, cmp.InInventory)
        # esper.delete_entity(selection) can't delete bc then its effect fizzles
        event.Tick()
        scene.to_phase(scene.Phase.level, NPCTurn)


@dataclass
class Upkeep(esper.Processor):
    """apply and tick down Conditions"""

    def process(self) -> None:
        if not event.Queues.tick:
            return
        event.Queues.tick.clear()
        for entity, (status,) in ecs.Query(cmp.State):
            for status_effect, duration in list(status.map.items()):
                condition.apply(entity, status_effect, duration)
                status.map[status_effect] = max(0, duration - 1)
                if status.map[status_effect] == 0:
                    del status.map[status_effect]
