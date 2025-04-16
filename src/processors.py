import random
from dataclasses import dataclass

import esper
import tcod
from tcod import libtcodpy
from tcod.map import compute_fov

import components as cmp
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
    board: location.Board

    def process(self):
        while event.Queues.movement:
            movement = event.Queues.movement.pop()
            ent = movement.source
            move_x = movement.x
            move_y = movement.y
            if not esper.entity_exists(ent):  # entity intends to move, but dies first
                continue

            pos = esper.component_for_entity(ent, cmp.Position)
            new_x = pos.x + move_x
            new_y = pos.y + move_y
            # Note: as written, walking into a wall consumes a turn
            move = True
            self.board.build_entity_cache()  # expensive, but okay
            for target in self.board.entities[new_x][new_y]:
                ent_is_actor = esper.has_component(ent, cmp.Actor)
                if ent_is_actor and esper.has_component(target, cmp.Blocking):
                    move = False
                    src_is_enemy = esper.has_component(ent, cmp.Enemy)
                    target_is_harmable = esper.has_component(target, cmp.Actor)
                    if src_is_enemy and target_is_harmable:
                        event.Damage(ent, target, 1)
                        # this should come from some property on the source
                ent_is_player = esper.has_component(ent, cmp.Player)
                target_is_collectable = esper.has_component(target, cmp.Collectable)
                if ent_is_player and target_is_collectable:
                    esper.remove_component(target, cmp.Position)
                    esper.add_component(target, cmp.InInventory())
                    create.inventory_map()
                    message = "player picked up an item"
                    event.Log.append(message)
                    # oneshot call some collectable processor?

            if move:
                pos.x = new_x
                pos.y = new_y
                self.board.entities[new_x][new_y].add(ent)


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
                    func, args = self.action_map[input_event.sym]
                    func(*args)
                    listen = False


@dataclass
class GameInputEventProcessor(InputEventProcessor):
    def __init__(self):
        player, _ = ecs.Query(cmp.Player).first()
        self.action_map = {
            input.KEYMAP[input.Input.MOVE_DOWN]: (event.Movement, [player, 0, 1]),
            input.KEYMAP[input.Input.MOVE_LEFT]: (event.Movement, [player, -1, 0]),
            input.KEYMAP[input.Input.MOVE_UP]: (event.Movement, [player, 0, -1]),
            input.KEYMAP[input.Input.MOVE_RIGHT]: (event.Movement, [player, 1, 0]),
            input.KEYMAP[input.Input.ESC]: (scene.to_phase, [scene.Phase.menu]),
            input.KEYMAP[input.Input.ONE]: (self.to_target, [1]),
            input.KEYMAP[input.Input.TWO]: (self.to_target, [2]),
            input.KEYMAP[input.Input.TAB]: (scene.to_phase, [scene.Phase.inventory]),
        }

    def to_target(self, slot: int):
        # TODO: This probably wants to take spell_ent and not slot num
        player_pos = location.player_position()
        xhair_pos = next(ecs.Query(cmp.Crosshair, cmp.Position).first_cmp(cmp.Position))
        xhair_pos.x, xhair_pos.y = player_pos.x, player_pos.y

        for spell_ent, (spell_cmp) in esper.get_component(cmp.Spell):
            if spell_cmp.slot == slot:
                esper.add_component(spell_ent, cmp.CurrentSpell())

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
        for entity, melee in esper.get_component(cmp.Melee):
            epos = esper.component_for_entity(entity, cmp.Position)
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
        actor = next(ecs.Query(cmp.Player, cmp.Actor).first_cmp(cmp.Actor))
        self.render_bar(1, 1, actor.hp, actor.max_hp, display.PANEL_WIDTH - 2)

        # inventory
        inv_map = create.inventory_map()
        for i, (name, entities) in enumerate(inv_map):
            self.console.print(1, 3 + i, f"{len(entities)}x {name}")

        # spells
        self.console.print(1, 8, "-" * (display.PANEL_WIDTH - 2))
        spells = ecs.Query(cmp.Spell, cmp.Onymous).get()
        for i, (_, (spell_cmp, named)) in enumerate(spells):
            text = f"Slot {spell_cmp.slot}: {named.name}"
            # TODO: 9 is arbitrary
            self.console.print(1, 9 + i, text)

        # right panel
        self.console.draw_frame(x=display.R_PANEL_START, **panel_params)
        for i, message in enumerate(event.Log.messages):
            self.console.print(1 + display.R_PANEL_START, 1 + i, message)

    def _apply_lighting(self, gameboard, cell_rgbs, in_fov) -> list[list[typ.CELL_RGB]]:
        """display cells in fov with lighting, explored without, and hide the rest"""
        for x, col in enumerate(cell_rgbs):
            for y, (glyph, fgcolor, _) in enumerate(col):
                cell = gameboard.get_cell(x, y)
                if not cell:
                    continue
                if in_fov[x][y]:
                    gameboard.explored.add(cell)
                    brighter = display.brighter(fgcolor, scale=100)
                    cell_rgbs[x][y] = (glyph, brighter, display.Color.CANDLE)
                elif cell in gameboard.explored:
                    cell_rgbs[x][y] = (glyph, fgcolor, display.Color.BLACK)
                else:
                    cell_rgbs[x][y] = (glyph, display.Color.BLACK, display.Color.BLACK)
        return cell_rgbs

    def _get_fov(self, board: location.Board):
        transparency = board.as_transparency()
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
    board: location.Board

    def _board_to_cell_rgbs(self, board: location.Board):
        cell_rgbs = [list(map(board.as_rgb, row)) for row in board.cells]

        in_fov = self._get_fov(board)

        nonwall_drawables = ecs.Query(cmp.Position, cmp.Visible).exclude(cmp.Cell).get()
        for _, (pos, vis) in nonwall_drawables:
            if not in_fov[pos.x][pos.y]:
                continue
            cell_rgbs[pos.x][pos.y] = (vis.glyph, vis.color, vis.bg_color)

        cell_rgbs = self._apply_lighting(board, cell_rgbs, in_fov)
        return cell_rgbs

    def process(self):
        self.console.clear()
        self._draw_panels()
        cell_rgbs = self._board_to_cell_rgbs(self.board)
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
            input.KEYMAP[input.Input.ESC]: (self.exit, []),
            input.KEYMAP[input.Input.SELECT]: (scene.to_phase, [scene.Phase.level]),
        }


@dataclass
class TargetInputEventProcessor(InputEventProcessor):
    board: location.Board

    def __init__(self, board):
        self.board = board
        pos = next(ecs.Query(cmp.Crosshair, cmp.Position).first_cmp(cmp.Position))
        to_level = (scene.to_phase, [scene.Phase.level])
        # TODO: esc out of target mode allows skeletons a turn, when it shouldn't

        self.action_map = {
            input.KEYMAP[input.Input.MOVE_DOWN]: (self.move_crosshair, [0, 1]),
            input.KEYMAP[input.Input.MOVE_LEFT]: (self.move_crosshair, [-1, 0]),
            input.KEYMAP[input.Input.MOVE_UP]: (self.move_crosshair, [0, -1]),
            input.KEYMAP[input.Input.MOVE_RIGHT]: (self.move_crosshair, [1, 0]),
            input.KEYMAP[input.Input.ESC]: to_level,
            input.KEYMAP[input.Input.SELECT]: (self.spell_to_events, [pos]),
        }

    def move_crosshair(self, x, y):
        crosshair, (_, pos) = ecs.Query(cmp.Crosshair, cmp.Position).first()
        spell_cmp = next(ecs.Query(cmp.Spell, cmp.CurrentSpell).first_cmp(cmp.Spell))

        player_pos = location.player_position()
        new_pos = cmp.Position(pos.x + x, pos.y + y)
        dist_to_player = location.euclidean_distance(player_pos, new_pos)
        if dist_to_player < spell_cmp.target_range:
            event.Movement(crosshair, x, y)

    def spell_to_events(self, pos):
        self.board.build_entity_cache()  # expensive, but okay

        spell_ent, _ = ecs.Query(cmp.Spell, cmp.CurrentSpell).first()

        player_pos = location.player_position()
        dmg_effect = esper.try_component(spell_ent, cmp.DamageEffect)
        if dmg_effect:
            for target in self.board.entities[pos.x][pos.y]:
                if esper.has_component(target, cmp.Actor):
                    event.Damage(dmg_effect.source, target, dmg_effect.amount)

        move_effect = esper.try_component(spell_ent, cmp.MoveEffect)
        if move_effect:
            x = pos.x - player_pos.x
            y = pos.y - player_pos.y
            event.Movement(move_effect.target, x, y)

        esper.remove_component(spell_ent, cmp.CurrentSpell)
        scene.to_phase(scene.Phase.level, NPCProcessor)


@dataclass
class TargetRenderProcessor(BoardRenderProcessor):
    console: tcod.console.Console
    context: tcod.context.Context
    board: location.Board

    def process(self) -> None:
        self.console.clear()
        self._draw_panels()

        cell_rgbs = self._board_to_cell_rgbs(self.board)

        drawable_areas = ecs.Query(cmp.Position, cmp.EffectArea).get()
        for _, (pos, aoe) in drawable_areas:
            cell = cell_rgbs[pos.x][pos.y]
            cell_rgbs[pos.x][pos.y] = cell[0], cell[1], aoe.color

        self.present(cell_rgbs)


@dataclass
class InventoryRenderProcessor(BoardRenderProcessor):
    console: tcod.console.Console
    context: tcod.context.Context
    board: location.Board

    def display_inventory(self):
        menu_selection = next(ecs.Query(cmp.MenuSelection).first_cmp())

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

        cell_rgbs = self._board_to_cell_rgbs(self.board)

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
            input.KEYMAP[input.Input.SELECT]: (self.use_item, []),
        }

    def move_selection(self, diff: int):
        menu_selection = next(ecs.Query(cmp.MenuSelection).first_cmp())
        menu_selection.item += diff

    def use_item(self):
        inv_map = create.inventory_map()
        menu_selection = next(ecs.Query(cmp.MenuSelection).first_cmp())
        name = inv_map[menu_selection.item][0]
        selection = inv_map[menu_selection.item][1].pop()
        print(f"using {name}: {selection}")

        heal_effect = esper.try_component(selection, cmp.HealEffect)
        player, _ = ecs.Query(cmp.Player).first()
        if heal_effect:
            event.Damage(selection, player, -1 * heal_effect.amount)

        # esper.delete_entity(selection)
        esper.remove_component(selection, cmp.InInventory)
        # TODO: if inventory is empty, fail to go to inventory mode?

        scene.to_phase(scene.Phase.level, NPCProcessor)


@dataclass
class UpkeepProcessor(InputEventProcessor):
    """tick down all Conditions"""

    def process(self) -> None:
        for _, (status,) in ecs.Query(cmp.State).get():
            for condition, val in status.map:
                status.map[condition] = max(0, val - 1)
                if status.map[condition] == 0:
                    del status.map[condition]
