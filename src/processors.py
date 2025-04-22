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

# TODO: I'm namespacing the processors, but I should probably break them down by phase?


@dataclass
class MovementProcessor(esper.Processor):
    # TODO: lots of stuff is happening here. Good idea to break up the proccess func

    def process(self):
        board = location.BOARD
        while event.Queues.movement:
            movement = event.Queues.movement.pop()
            ent = movement.source
            move_x = movement.x
            move_y = movement.y
            if not esper.entity_exists(ent):  
                # entity intends to move, but dies first
                continue

            ent_is_player = esper.has_component(ent, cmp.Player)
            pos = esper.component_for_entity(ent, cmp.Position)
            new_x = pos.x + move_x
            new_y = pos.y + move_y
            move = True
            board.build_entity_cache()  # keyerror if this isn't here
            for target in board.entities[new_x][new_y]:
                ent_is_actor = esper.has_component(ent, cmp.Actor)
                if ent_is_actor and esper.has_component(target, cmp.Blocking):
                    move = False
                    src_is_enemy = esper.has_component(ent, cmp.Enemy)
                    target_is_harmable = esper.has_component(target, cmp.Actor)
                    if src_is_enemy and target_is_harmable:
                        event.Damage(ent, target, 1)
                        # this should come from some property on the source
                        # should it be a DamageEffect?
                    if ent_is_player:
                        # Note: walking into a wall consumes a turn
                        message = f"Failed to move to invalid location"
                        event.Log.append(message)

                target_is_collectable = esper.has_component(target, cmp.Collectable)
                if ent_is_player and target_is_collectable:
                    esper.remove_component(target, cmp.Position)
                    esper.add_component(target, cmp.InInventory())
                    create.inventory_map()
                    name = esper.component_for_entity(target, cmp.Onymous).name
                    message = f"player picked up {name}"
                    event.Log.append(message)
                    # oneshot call some collectable processor?
                target_is_trap = esper.has_component(target, cmp.Trap)
                ent_flies = esper.has_component(ent, cmp.Flying)
                if ent_is_actor and target_is_trap and not ent_flies:
                    if esper.has_component(target, cmp.DamageEffect):
                        esper.add_component(target, cmp.Target(target=ent))
                    event.effects_to_events(target)

            if move:
                board.entities[pos.x][pos.y].remove(ent)
                pos.x, pos.y = new_x, new_y
                board.entities[new_x][new_y].add(ent)


@dataclass
class DamageProcessor(esper.Processor):
    def process(self):
        while event.Queues.damage:
            damage = event.Queues.damage.pop()
            if not all(map(esper.entity_exists, [damage.target, damage.source])):
                # if either entity doesn't exist anymore, damage fizzles
                continue

            actor = esper.component_for_entity(damage.target, cmp.Actor)
            actor.hp -= damage.amount
            actor.hp = min(actor.max_hp, max(0, actor.hp))  # between 0 and max

            to_name = lambda x: esper.component_for_entity(x, cmp.Onymous).name
            src_name = to_name(damage.source)
            target_name = to_name(damage.target)

            message = f"{src_name} heals {-1 * damage.amount} to {target_name}"
            if damage.amount > 0:
                message = f"{src_name} deals {damage.amount} to {target_name}"
            event.Log.append(message)

            if actor.hp <= 0:
                message = f"{target_name} is no more"
                event.Log.append(message)
                esper.delete_entity(damage.target, immediate=True)
                # crashes if player gets deleted
        # this probably not where we process death
        # death can potentially happen without damage


@dataclass
class InputEventProcessor(esper.Processor):
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
                    except typ.InvalidAction:
                        print("caught invalid action")
                    else:
                        listen = False


@dataclass
class GameInputEventProcessor(InputEventProcessor):
    def __init__(self):
        self.action_map = {
            input.KEYMAP[input.Input.MOVE_DOWN]: (self.move, [0, 1]),
            input.KEYMAP[input.Input.MOVE_LEFT]: (self.move, [-1, 0]),
            input.KEYMAP[input.Input.MOVE_UP]: (self.move, [0, -1]),
            input.KEYMAP[input.Input.MOVE_RIGHT]: (self.move, [1, 0]),
            input.KEYMAP[input.Input.ESC]: (scene.to_phase, [scene.Phase.menu]),
            input.KEYMAP[input.Input.ONE]: (self.to_target, [1]),
            input.KEYMAP[input.Input.TWO]: (self.to_target, [2]),
            input.KEYMAP[input.Input.TAB]: (scene.to_phase, [scene.Phase.inventory]),
            input.KEYMAP[input.Input.SKIP]: self.skip,
        }

    def skip(self):
        event.Tick()


    def move(self, x, y):
        player = ecs.Query(cmp.Player).first()
        event.Movement(player, x, y)
        event.Tick()

    def to_target(self, slot: int):
        # TODO: This probably wants to take spell_ent and not slot num
        player_pos = location.player_position()
        xhair_ent = ecs.Query(cmp.Crosshair, cmp.Position).first()
        xhair_pos = ecs.cmps[xhair_ent][cmp.Position]

        xhair_pos.x = player_pos.x
        xhair_pos.y = player_pos.y

        casting_spell = None
        for spell_ent, (spell_cmp) in esper.get_component(cmp.Spell):
            if spell_cmp.slot == slot:
                casting_spell = spell_ent

        if not casting_spell:
            return
        if condition.has(casting_spell, typ.Condition.Cooldown):
            event.Log.append("spell on cooldown")
            scene.oneshot(BoardRenderProcessor)
            raise typ.InvalidAction
        esper.add_component(casting_spell, cmp.Targeting())
        scene.to_phase(scene.Phase.target)


@dataclass
class NPCProcessor(esper.Processor):
    def process(self):
        for entity, _ in esper.get_component(cmp.Wander):
            dir = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0), (0, 0)])
            if dir == (0, 0):
                continue
            event.Movement(entity, *dir)

        player_pos = location.player_position()
        for entity, (melee, epos) in ecs.Query(cmp.Melee, cmp.Position):
            dist_to_player = location.euclidean_distance(player_pos, epos)
            if dist_to_player > melee.radius:
                continue
            # Naive pathfinding. Does not deal with corners well
            if player_pos.x > epos.x:
                event.Movement(entity, x=1, y=0)
            elif player_pos.y > epos.y:
                event.Movement(entity, x=0, y=1)
            elif player_pos.x < epos.x:
                event.Movement(entity, x=-1, y=0)
            elif player_pos.y < epos.y:
                event.Movement(entity, x=0, y=-1)


@dataclass
class RenderProcessor(esper.Processor):
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

        # left panel
        self.console.draw_frame(x=0, **panel_params)
        actor = ecs.Query(cmp.Player, cmp.Actor).cmp(cmp.Actor)
        self.render_bar(1, 1, actor.hp, actor.max_hp, display.PANEL_WIDTH - 2)

        # inventory
        inv_map = create.inventory_map()
        for i, (name, entities) in enumerate(inv_map):
            self.console.print(1, 3 + i, f"{len(entities)}x {name}")

        # spells
        self.console.print(1, 8, "-" * (display.PANEL_WIDTH - 2))
        spells = ecs.Query(cmp.Spell, cmp.Onymous)
        for i, (spell_ent, (spell_cmp, named)) in enumerate(sorted(spells)):
            # TODO: 9 is arbitrary
            text = f"Slot{spell_cmp.slot}:{named.name}"
            if cd := condition.get_val(spell_ent, typ.Condition.Cooldown):
                text = f"{text}:{typ.Condition.Cooldown.name} {cd}"
            self.console.print(1, 9 + i, text)

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
        fov = compute_fov(transparency, (pos.x, pos.y), radius=4, algorithm=algo)
        return fov

    def present(self, cell_rgbs):
        startx, endx = (display.PANEL_WIDTH, display.R_PANEL_START)
        starty, endy = (0, display.BOARD_HEIGHT)
        self.console.rgb[startx:endx, starty:endy] = cell_rgbs
        self.context.present(self.console)  # , integer_scaling=True


@dataclass
class BoardRenderProcessor(RenderProcessor):
    console: tcod.console.Console
    context: tcod.context.Context

    def _get_cell_rgbs(self):
        board = location.BOARD
        cell_rgbs = [list(map(board.as_rgb, row)) for row in board.cells]

        in_fov = self._get_fov()

        nonwall_drawables = ecs.Query(cmp.Position, cmp.Visible).exclude(cmp.Cell)
        for _, (pos, vis) in nonwall_drawables:
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
class MenuRenderProcessor(esper.Processor):
    context: tcod.context.Context
    console: tcod.console.Console

    def process(self):
        self.console.clear()
        x = display.PANEL_WIDTH + (display.BOARD_WIDTH // 2)
        y = display.BOARD_HEIGHT // 2
        self.console.print(x, y, "WELCOME TO MALEFICER", alignment=libtcodpy.CENTER)
        self.context.present(self.console)  # , integer_scaling=True


@dataclass
class MenuInputEventProcessor(InputEventProcessor):
    def __init__(self):
        self.action_map = {
            input.KEYMAP[input.Input.ESC]: self.exit,
            input.KEYMAP[input.Input.SELECT]: (scene.to_phase, [scene.Phase.level]),
        }


@dataclass
class TargetInputEventProcessor(InputEventProcessor):

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
            cell = location.BOARD.cells[xhair_pos.x][xhair_pos.y]
            trg = cmp.Target(target=cell)
            esper.add_component(targeting_entity, trg)

        event.effects_to_events(targeting_entity)
        esper.remove_component(targeting_entity, cmp.Targeting)
        event.Tick()
        scene.to_phase(scene.Phase.level, NPCProcessor)


@dataclass
class TargetRenderProcessor(BoardRenderProcessor):
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
class InventoryRenderProcessor(BoardRenderProcessor):
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
class InventoryInputEventProcessor(InputEventProcessor):
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
        menu_selection.item += diff

    def use_item(self):
        inv_map = create.inventory_map()
        menu_selection = ecs.Query(cmp.MenuSelection).cmp(cmp.MenuSelection)
        name = inv_map[menu_selection.item][0]
        selection = inv_map[menu_selection.item][1].pop()
        print(f"using {name}: {selection}")

        event.effects_to_events(selection)

        # esper.delete_entity(selection)
        esper.remove_component(selection, cmp.InInventory)
        # TODO: if inventory is empty, fail to go to inventory mode?
        event.Tick()
        scene.to_phase(scene.Phase.level, NPCProcessor)


@dataclass
class UpkeepProcessor(esper.Processor):
    """tick down all Conditions"""

    def process(self) -> None:
        if not event.Queues.tick:
            return
        event.Queues.tick.clear()
        for _, (status,) in ecs.Query(cmp.State):
            for condition in list(status.map.keys()):
                status.map[condition] = max(0, status.map[condition] - 1)
                if status.map[condition] == 0:
                    del status.map[condition]
