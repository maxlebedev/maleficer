import collections
import itertools
from dataclasses import dataclass

import time
import esper
import tcod
from tcod import libtcodpy

import behavior
import components as cmp
import condition
import create
import display
import ecs
import event
import input
import location
import math_util
import typ
import phase


PROC_QUEUE = collections.deque()


def get_selected_menuitem():
    """assumes inventory has at least one item"""
    # TODO: move the code somewhere
    inv_map = create.player.inventory_map()
    menu_selection = ecs.Query(cmp.MenuSelection, cmp.InventoryMenu).cmp(0)
    menu_selection.item = math_util.clamp(menu_selection.item, len(inv_map) - 1)

    selection = inv_map[menu_selection.item][1].pop()

    return selection


def queue_proc(proctype: type[esper.Processor]):
    if proc_instance := esper.get_processor(proctype):
        if proc_instance in PROC_QUEUE:
            return

        PROC_QUEUE.appendleft(proc_instance)


class Processor(esper.Processor):
    def _process(self):
        raise NotImplementedError

    def process(self):
        game_meta = ecs.Query(cmp.GameMeta).val

        if self == game_meta.process:
            # print(f"running {self.__class__}")
            self._process()
            game_meta.process = PROC_QUEUE.popleft()


@dataclass
class Enqueue(Processor):
    _phase: "phase.Ontology"

    def _process(self):
        PROC_QUEUE.clear()
        for procs in phase.ALL[self._phase]:
            PROC_QUEUE.append(procs)


@dataclass
class Movement(Processor):
    def bump(self, source, target):
        """one entity bumps into another"""

        if esper.has_component(source, cmp.Player):
            # Note: walking into a wall consumes a turn
            if door_cmp := esper.try_component(target, cmp.Door):
                door_cmp.closed = False
                esper.remove_component(target, cmp.Blocking)
                esper.remove_component(target, cmp.Opaque)
                vis = esper.component_for_entity(target, cmp.Visible)
                vis.glyph = display.Glyph.ODOOR
            else:
                event.Log.append("can't move there")
                esper.dispatch_event("flash")

    def pick_up(self, target):
        """pick up an item"""
        board = location.get_board()
        board.remove(target)
        esper.add_component(target, cmp.InInventory())
        name = event.Log.color_fmt(target)
        event.Log.append(f"picked up {name}")
        # oneshot call some collectable processor?

    def _process(self):
        board = location.get_board()
        while event.Queues.movement:
            movement = event.Queues.movement.popleft()  # left so player first
            mover = movement.source
            if condition.has(mover, typ.Condition.Stun):
                continue

            if not esper.entity_exists(mover):
                # entity intends to move, but dies first
                continue

            has = esper.has_component

            pos = esper.component_for_entity(mover, cmp.Position)
            new_x, new_y = movement.x, movement.y
            if movement.relative:
                new_x += pos.x
                new_y += pos.y

            if last_pos := esper.try_component(mover, cmp.LastPosition):
                last_pos.pos.x = pos.x
                last_pos.pos.y = pos.y

            targets = {e for e in board.entities[new_x][new_y]}

            blocked = any(has(target, cmp.Blocking) for target in targets)
            if has(mover, cmp.Crosshair) or not blocked:
                board.reposition(mover, new_x, new_y)

            if not has(mover, cmp.Health):
                continue

            for target in targets:
                if has(target, cmp.Blocking):
                    self.bump(mover, target)

                if has(mover, cmp.Player) and has(target, cmp.Collectable):
                    self.pick_up(target)

                ent_flies = esper.has_component(mover, cmp.Flying)
                if not ent_flies and has(target, cmp.OnStep):
                    esper.add_component(target, cmp.Target(target=mover))
                    event.trigger_all_callbacks(target, cmp.StepTrigger)


@dataclass
class NPCEval(Processor):
    def _process(self):
        enemies = ecs.Query(cmp.Enemy)
        stunned_txt = display.colored_text("stunned", display.Color.CYAN)

        for entity, (en_cmp,) in enemies:
            if condition.has(entity, typ.Condition.Stun):
                name = event.Log.color_fmt(entity)
                event.Log.append(f"{name} is {stunned_txt}")
                continue

            if en_cmp.evaluate:
                if action := en_cmp.evaluate(entity):
                    esper.add_component(entity, cmp.Intent(action=action))


@dataclass
class NPCAct(Processor):
    def _process(self):
        enemies = ecs.Query(cmp.Enemy, cmp.Intent)
        for entity, (_, intent) in enemies:
            intent.action(entity)
            esper.remove_component(entity, cmp.Intent)


@dataclass
class Damage(Processor):
    def _make_message(self, damage):
        source_name = damage.source[cmp.KnownAs].name
        if cmp.Visible in damage.source:
            src_color = damage.source[cmp.Visible].color
            source_name = display.colored_text(source_name, src_color)
        target_name = event.Log.color_fmt(damage.target)
        # target_name = f"{target_name}#{damage.target}"

        if damage.amount >= 0:
            amount = display.colored_text(damage.amount, display.Color.RED)
            return f"{source_name} deals {amount} damage to {target_name}"
        amount = display.colored_text(-1 * damage.amount, display.Color.GREEN)
        return f"{source_name} heals {target_name} for {amount}"

    def _resolve_cell_damage(self, damage_event):
        board = location.get_board()
        pos = esper.component_for_entity(damage_event.target, cmp.Position)
        entities = board.pieces_at(*pos)
        for ent in entities:
            if esper.has_component(ent, cmp.Health):
                event.Damage(damage_event.source, ent, damage_event.amount)

    def _resolve_aegis(self, damage_event):
        aegis = condition.get_val(damage_event.target, typ.Condition.Aegis)
        absorbed = min(aegis, damage_event.amount)
        damage_event.amount -= absorbed
        aegis -= absorbed
        condition.grant(damage_event.target, typ.Condition.Aegis, aegis)

        dmg = display.colored_text(str(absorbed), display.Color.CYAN)
        aegis = display.colored_text("Aegis", display.Color.CYAN)
        event.Log.append(f"{aegis} absorbs {dmg} damage")

    def _process(self):
        while event.Queues.damage:
            damage_event = event.Queues.damage.popleft()
            if not esper.entity_exists(damage_event.target):
                # if entity doesn't exist anymore, damage fizzles
                continue
            if esper.has_component(damage_event.target, cmp.Cell):
                self._resolve_cell_damage(damage_event)
            if not esper.has_component(damage_event.target, cmp.Health):
                # damage source hit a wall, or similar
                continue

            if condition.has(damage_event.target, typ.Condition.Aegis):
                self._resolve_aegis(damage_event)

            math_util.apply_damage(damage_event.target, damage_event.amount)

            message = self._make_message(damage_event)

            if cmp.Position not in damage_event.source or location.player_hears(
                damage_event.source[cmp.Position]
            ):
                event.Log.append(message)


@dataclass
class Death(Processor):
    def queue_zero_health(self):
        for ent, (hp,) in ecs.Query(cmp.Health):
            if hp.current <= 0:
                event.Death(ent)

    def _process(self):
        board = location.get_board()

        self.queue_zero_health()
        while event.Queues.death:
            killable = event.Queues.death.popleft().entity
            if not esper.entity_exists(killable):
                continue

            pos = esper.component_for_entity(killable, cmp.Position)
            if killable_cell := board.get_cell(*pos):
                esper.add_component(killable, cmp.Target(target=killable_cell))
                event.trigger_all_callbacks(killable, cmp.DeathTrigger)
            if location.player_hears(pos):
                name = event.Log.color_fmt(killable)
                # message = f"{name}#{killable} is no more"
                message = f"{name} is no more"
                event.Log.append(message)
            if esper.has_component(killable, cmp.Cell):
                floor = create.tile.floor(pos.x, pos.y)
                board.set_cell(pos.x, pos.y, floor)
                board.build_entity_cache()
            else:
                board.remove(killable)
                player = ecs.Query(cmp.Player).first()
                if player == killable:
                    phase.change_to(phase.Ontology.game_over)
                    create.ui.end_game()
                esper.delete_entity(killable, immediate=True)
            self.queue_zero_health()


@dataclass
class InputEvent(Processor):
    action_map = {}

    def exit(self):
        raise SystemExit()

    def _process(self):
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
            input.KEYMAP[input.Input.ESC]: (
                phase.change_to,
                [phase.Ontology.main_menu],
            ),
            input.KEYMAP[input.Input.SPELL1]: (self.handle_slot_key, [1]),
            input.KEYMAP[input.Input.SPELL2]: (self.handle_slot_key, [2]),
            input.KEYMAP[input.Input.SPELL3]: (self.handle_slot_key, [3]),
            input.KEYMAP[input.Input.SPELL4]: (self.handle_slot_key, [4]),
            input.KEYMAP[input.Input.INVENTORY]: self.to_inventory,
            input.KEYMAP[input.Input.SKIP]: self.skip,
        }

    def to_inventory(self):
        try:
            ecs.Query(cmp.InInventory).first()
        except KeyError:
            raise typ.InvalidAction

        phase.change_to(phase.Ontology.inventory)

    def skip(self):
        event.Tick()

    def move(self, x, y):
        player = ecs.Query(cmp.Player).first()
        event.Movement(player, x, y, relative=True)
        event.Tick()

    def handle_slot_key(self, slot: int):
        state = tcod.event.get_keyboard_state()
        alt_key = input.KEYMAP[input.Input.ALTERNATE]
        if state[alt_key.scancode]:
            self.unlearn(slot)
            return
        self.to_target(slot)

    def unlearn(self, slot: int):
        """take a spell and turn it into a scroll"""
        unlearned = False
        for spell_ent, (attuned) in esper.get_component(cmp.Attuned):
            if attuned.slot == slot:
                esper.remove_component(spell_ent, cmp.Attuned)
                scroll = create.item.scroll(spell=spell_ent)
                esper.add_component(scroll, cmp.InInventory())
                unlearned = True
                event.Tick()
                phase.change_to(phase.Ontology.level, NPCEval)
        if not unlearned:
            esper.dispatch_event("flash")
            event.Log.append("can't unlearn, spell doesn't exist")

    def to_target(self, slot: int):
        # TODO: This probably wants to take spell_ent and not slot num
        board = location.get_board()

        casting_spell = None
        for spell_ent, (attuned) in esper.get_component(cmp.Attuned):
            if attuned.slot == slot:
                casting_spell = spell_ent

        if not casting_spell:
            raise typ.InvalidAction("spell doesn't exist")
        if condition.has(casting_spell, typ.Condition.Cooldown):
            raise typ.InvalidAction("spell on cooldown")

        player_pos = location.player_position()
        xhair_ent = ecs.Query(cmp.Crosshair, cmp.Position).first()
        board.reposition(xhair_ent, *player_pos)
        esper.add_component(casting_spell, cmp.Targeting())
        phase.change_to(phase.Ontology.target)


@dataclass
class Render(Processor):
    context: tcod.context.Context
    console: tcod.console.Console

    dashes = "├" + "─" * (display.PANEL_IWIDTH) + "┤"

    def left_print(self, *args, **kwargs):
        self.console.print(alignment=libtcodpy.LEFT, *args, **kwargs)

    def center_print(self, *args, **kwargs):
        self.console.print(alignment=libtcodpy.CENTER, *args, **kwargs)

    def right_print(self, *args, **kwargs):
        self.console.print(alignment=libtcodpy.RIGHT, *args, **kwargs)

    def present(self, cell_rgbs):
        display.write_rgbs(self.console, cell_rgbs)
        self.context.present(self.console)


@dataclass
class BoardRender(Render):
    context: tcod.context.Context
    console: tcod.console.Console

    def render_bar(self, x: int, y: int, curr: int, maximum: int, width: int):
        bar_width = int(curr / maximum * width)
        bg = display.Color.BAR_EMPTY
        bar_args = {"x": x, "y": y, "height": 1, "ch": 1, "bg": bg}

        self.console.draw_rect(width=width, **bar_args)

        if bar_width > 0:
            bar_args["bg"] = display.Color.BAR_FILLED
            self.console.draw_rect(width=bar_width, **bar_args)

        text = f"HP: {curr}/{maximum}"
        self.console.print(x=x, y=y, string=text, fg=display.Color.BLACK)

    def _draw_selection_info(self, item: typ.Entity):
        selection_info = []
        spell_component_details = [
            ("Damage", cmp.DamageEffect, "desc"),
            ("Heal", cmp.HealEffect, "amount"),
            ("Range", cmp.Spell, "target_range"),
            ("Cooldown", cmp.Cooldown, "turns"),
        ]
        for name, try_cmp, attr in spell_component_details:
            if component := esper.try_component(item, try_cmp):
                value = getattr(component, attr)
                selection_info.append(f"{name}:{value}")
        if bleed_effect := esper.try_component(item, cmp.BleedEffect):
            message = f"Grants Bleed:{bleed_effect.value}"
            selection_info.append(message)
        if push := esper.try_component(item, cmp.PushEffect):
            message = f"Imposes Push:{push.distance}"
            selection_info.append(message)
        if stun_effect := esper.try_component(item, cmp.StunEffect):
            message = f"Grants Stun:{stun_effect.value}"
            selection_info.append(message)
        if aoe := esper.try_component(item, cmp.EffectArea):
            # callback kwargs into spell info
            # this may not be right for other callbacks
            for name, value in aoe.callback.keywords.items():
                message = f"{name.title()}:{value}"
                selection_info.append(message)
        return selection_info

    def _spell_section(self):
        spells = ecs.Query(cmp.Spell, cmp.KnownAs, cmp.Attuned)
        sorted_spells = sorted(spells, key=lambda x: x[1][2].slot)

        for spell_ent, (_, named, attuned) in sorted_spells:
            text = f"Slot{attuned.slot}:{named.name}"
            if cd := condition.get_val(spell_ent, typ.Condition.Cooldown):
                text = f"{text}:{typ.Condition.Cooldown.name} {cd}"
            fg = display.Color.BEIGE
            bg = display.Color.BLACK
            if esper.has_component(spell_ent, cmp.Targeting):
                fg, bg = bg, fg
            yield (text, fg, bg)

    def _right_panel(self, panel_params):
        self.console.draw_frame(x=display.R_PANEL_START, **panel_params)
        panel_params["x"] = display.R_PANEL_START + 1
        panel_params["y"] = 1
        panel_params["width"] = display.PANEL_IWIDTH
        panel_params["height"] = display.PANEL_IHEIGHT

        message = "\n".join([m[0] for m in event.Log.messages])
        self.console.print_box(string=message, **panel_params)

    def _left_panel(self, panel_params):
        self.console.draw_frame(x=0, **panel_params)
        hp = ecs.Query(cmp.Player, cmp.Health).cmp(1)
        self.render_bar(1, 1, hp.current, hp.max, display.PANEL_IWIDTH)

        panel_contents = []

        panel_contents += self._inventory()
        panel_contents.append(None)

        panel_contents += self._spell_section()
        panel_contents.append(None)

        game_meta = ecs.Query(cmp.GameMeta).val

        # if targeting, also print spell info
        if targeting := esper.get_component(cmp.Targeting):
            trg_ent, _ = targeting[0]
            panel_contents += self._draw_selection_info(trg_ent)
        elif isinstance(game_meta.process, InventoryRender):
            selection = get_selected_menuitem()
            if learnable := esper.try_component(selection, cmp.Learnable):
                selection = learnable.spell
            panel_contents += self._draw_selection_info(selection)

        for y_idx, content in enumerate(panel_contents, start=3):
            match content:
                case str():
                    self.console.print(1, y_idx, content)
                case tuple():
                    self.console.print(1, y_idx, *content)
                case None:
                    self.console.print(0, y_idx, self.dashes)

        map_info = ecs.Query(cmp.GameMeta).cmp(cmp.MapInfo)
        self.console.print(1, display.PANEL_IHEIGHT, f"Depth: {map_info.depth}")

        for i, cnd in enumerate(self.gather_conditions()):
            y = display.PANEL_IHEIGHT - i - 1
            self.console.print(1, y, cnd, fg=display.Color.YELLOW)

    def _inventory(self):
        inv_map = create.player.inventory_map()
        inventory = [f"{len(ent)}x {name}" for (name, ent) in inv_map]
        inventory += ["" for _ in range(4 - len(inv_map))]
        return inventory

    def _draw_panels(self):
        panel_params = {
            "y": 0,
            "width": display.PANEL_WIDTH,
            "height": display.PANEL_HEIGHT,
        }

        self._left_panel(panel_params)
        self._right_panel(panel_params)

    def gather_conditions(self):
        ret = []
        for _, (cnd_state, _) in ecs.Query(cmp.State, cmp.Player):
            for status_effect, duration in cnd_state.map.items():
                ret.append(f"{status_effect.name} {duration}")
        return ret

    def _apply_lighting(self, cell_rgbs, in_fov) -> list[list[typ.CELL_RGB]]:
        """display cells in fov with lighting, explored without, and hide the rest"""
        board = location.get_board()
        # for screenshots, debugging
        # for cell in board.as_sequence():
        #     location.Board.explored.add(cell)
        for x, col in enumerate(cell_rgbs):
            for y, (glyph, fgcolor, _) in enumerate(col):
                cell = board.get_cell(x, y)
                if not cell:
                    continue
                if in_fov[x][y]:
                    board.explored.add(cell)

                    if not esper.get_component(cmp.Targeting):
                        # TODO: or if not TargetRender:
                        brighter = display.brighter(fgcolor, scale=100)
                        cell_rgbs[x][y] = (glyph, brighter, location.backlight(x, y))
                elif cell in board.explored:
                    cell_rgbs[x][y] = (glyph, fgcolor, display.Color.BLACK)
                else:
                    cell_rgbs[x][y] = (
                        display.Glyph.NONE,
                        display.Color.BLACK,
                        display.Color.BLACK,
                    )
        return cell_rgbs

    def _get_cell_rgbs(self):
        board = location.get_board()

        cell_rgbs = [list(map(board.as_rgb, row)) for row in board.cells]

        in_fov = location.get_fov()

        for x, col in enumerate(in_fov):
            for y, show in enumerate(col):
                if not show:
                    continue
                pieces = board.pieces_at(x, y)
                if not pieces:
                    continue
                front = pieces.pop()
                for piece in pieces:
                    if esper.has_component(piece, cmp.Blocking):
                        # Blocking pieces have display precedence
                        front = piece
                if vis := esper.try_component(front, cmp.Visible):
                    cell_rgbs[x][y] = (vis.glyph, vis.color, vis.bg_color)

        cell_rgbs = self._apply_lighting(cell_rgbs, in_fov)

        aura_ents = ecs.Query(cmp.Position, cmp.Aura)
        for _, (pos, aura) in aura_ents:
            aura_cells = aura.callback(pos)
            for x, y in aura_cells:
                if not in_fov[x][y]:
                    continue
                cell = cell_rgbs[x][y]
                cell_rgbs[x][y] = cell[0], cell[1], aura.color

        return cell_rgbs

    def _process(self):
        self.console.clear()
        self._draw_panels()
        cell_rgbs = self._get_cell_rgbs()
        self.present(cell_rgbs)


@dataclass
class MenuRender(Render):
    context: tcod.context.Context
    console: tcod.console.Console
    menu_cmp: type
    title: str
    background: str

    def _process(self):
        self.console.clear()
        x = display.CENTER_W
        y = display.CENTER_H

        if self.background:
            (self.console,) = tcod.console.load_xp(self.background, order="F")

        self.center_print(x, y, self.title)

        menu_selection = ecs.Query(cmp.MenuSelection, self.menu_cmp).cmp(0)

        menu_elements = ecs.Query(cmp.MenuItem, self.menu_cmp, cmp.KnownAs)
        sorted_menu = sorted(menu_elements, key=lambda x: x[1][0].order)
        for i, (_, (mi, _, on)) in enumerate(sorted_menu):
            fg = display.Color.LGREY
            if menu_selection.item == mi.order:
                fg = display.Color.WHITE
            self.center_print(x=x, y=y + 2 + i, string=on.name, fg=fg)

        self.context.present(self.console)


@dataclass
class MenuInputEvent(InputEvent):
    def __init__(self, menu_cmp):
        self.menu_cmp = menu_cmp
        self.action_map = {
            input.KEYMAP[input.Input.MOVE_DOWN]: (self.move_selection, [1]),
            input.KEYMAP[input.Input.MOVE_UP]: (self.move_selection, [-1]),
            input.KEYMAP[input.Input.ESC]: self.back,
            input.KEYMAP[input.Input.SELECT]: self.select,
        }

    def back(self):
        if self.menu_cmp.prev:
            phase.change_to(self.menu_cmp.prev)

    def select(self):
        menu_selection = ecs.Query(cmp.MenuSelection, self.menu_cmp).cmp(0)
        for entity, (mi, _) in ecs.Query(cmp.MenuItem, self.menu_cmp):
            if mi.order == menu_selection.item:
                event.trigger_all_callbacks(entity, cmp.UseTrigger)

    def move_selection(self, diff: int):
        menu_selection = ecs.Query(cmp.MenuSelection, self.menu_cmp).cmp(0)
        menu_selection.item += diff

        tot_items = len([_ for _ in ecs.Query(cmp.MenuItem, self.menu_cmp)]) - 1
        menu_selection.item = math_util.clamp(menu_selection.item, tot_items)


@dataclass
class TargetInputEvent(InputEvent):
    piece_coords = []

    def __init__(self):
        self.action_map = {
            input.KEYMAP[input.Input.MOVE_DOWN]: (self.move_crosshair, [0, 1]),
            input.KEYMAP[input.Input.MOVE_LEFT]: (self.move_crosshair, [-1, 0]),
            input.KEYMAP[input.Input.MOVE_UP]: (self.move_crosshair, [0, -1]),
            input.KEYMAP[input.Input.MOVE_RIGHT]: (self.move_crosshair, [1, 0]),
            input.KEYMAP[input.Input.ESC]: self.to_level,
            input.KEYMAP[input.Input.SELECT]: self.select,
            input.KEYMAP[input.Input.TARGET]: self.tab_target,
        }

    def to_level(self):
        self.piece_coords = []
        spell_ent = ecs.Query(cmp.Targeting).first()
        esper.remove_component(spell_ent, cmp.Targeting)
        phase.change_to(phase.Ontology.level)

    def move_crosshair(self, x, y):
        crosshair = ecs.Query(cmp.Crosshair, cmp.Position).first()
        pos = ecs.cmps[crosshair][cmp.Position]

        # TODO: maybe break out range to its own cmp and check for it here
        spell_cmp = ecs.Query(cmp.Spell, cmp.Targeting).cmp(0)

        player_pos = location.player_position()
        new_pos = cmp.Position(pos.x + x, pos.y + y)
        dist_to_player = location.euclidean_distance(player_pos, new_pos)
        if not spell_cmp or dist_to_player <= spell_cmp.target_range:
            event.Movement(crosshair, x, y, relative=True)

    def tab_target(self):
        """build piece_coord list, jump xhair along list, flush cache on exit"""
        # TODO: make sure that player isn't the first item in the list

        if not self.piece_coords:
            player_pos = location.player_position()
            sight_radius = ecs.Query(cmp.Player).val.sight_radius
            coords = location.coords_within_radius(player_pos, sight_radius)
            board = location.get_board()
            for x, y in coords:
                if board.pieces_at(x, y):
                    self.piece_coords.append((x, y))

        target = self.piece_coords.pop(0)
        xhair_pos = ecs.Query(cmp.Crosshair, cmp.Position).cmp(1)
        xhair_pos.x, xhair_pos.y = target
        self.piece_coords.append(target)

    def select(self):
        self.piece_coords = []
        xhair_pos = ecs.Query(cmp.Crosshair, cmp.Position).cmp(1)
        targeting_entity = ecs.Query(cmp.Targeting).first()
        board = location.get_board()

        if not esper.has_component(targeting_entity, cmp.Target):
            cell = xhair_pos.lookup_in(board.cells)
            trg = cmp.Target(target=cell)
            esper.add_component(targeting_entity, trg)

        try:
            event.trigger_effect_callbacks(targeting_entity)
            esper.remove_component(targeting_entity, cmp.Targeting)
            event.Tick()
            phase.change_to(phase.Ontology.level, Damage)  # to FIRST dmg phase
        except typ.InvalidAction as e:
            esper.dispatch_event("flash")
            event.Log.append(str(e))


@dataclass
class TargetRender(BoardRender):
    context: tcod.context.Context
    console: tcod.console.Console

    def piece_to_description(self, piece):
        desc = []
        name = "???"
        if esper.try_component(piece, cmp.KnownAs):
            name = event.Log.color_fmt(piece)
        desc.append(f"Name: {name}")
        if health_cmp := esper.try_component(piece, cmp.Health):
            desc.append(f"HP: {health_cmp.current}")
        if enemy_cmp := esper.try_component(piece, cmp.Enemy):
            desc.append(f"Speed: {enemy_cmp.speed}")
        return desc

    def _right_panel(self, panel_params):
        self.console.draw_frame(x=display.R_PANEL_START, **panel_params)
        panel_params["x"] = display.R_PANEL_START + 1
        panel_params["y"] = 1
        panel_params["width"] = display.PANEL_IWIDTH
        panel_params["height"] = display.PANEL_IHEIGHT

        xhair_pos = ecs.Query(cmp.Crosshair).cmp(cmp.Position)
        board = location.get_board()

        coords = [xhair_pos.as_list]

        spell = ecs.Query(cmp.Targeting).first()
        if aoe := esper.try_component(spell, cmp.EffectArea):
            coords = aoe.callback(xhair_pos)

        pieces = [p for x, y in coords for p in board.pieces_at(x, y)]

        panel_contents = []

        player = ecs.Query(cmp.Player).first()
        player_cmp = ecs.Query(cmp.Player).val
        for piece in pieces:
            if location.can_see(player, piece, player_cmp.sight_radius):
                panel_contents += self.piece_to_description(piece)
                panel_contents.append(None)

        x = display.R_PANEL_START
        for y_idx, content in enumerate(panel_contents, start=1):
            match content:
                case str():
                    self.console.print(x + 1, y_idx, content)
                case None:
                    self.console.print(x, y_idx, self.dashes)

    def _process(self) -> None:
        self.console.clear()
        self._draw_panels()

        cell_rgbs = self._get_cell_rgbs()

        targeting_ent = ecs.Query(cmp.Targeting).first()
        pos = ecs.Query(cmp.Crosshair).cmp(cmp.Position)
        highlighted = [pos.as_list]

        if aoe := esper.try_component(targeting_ent, cmp.EffectArea):
            highlighted += aoe.callback(pos)

        if spell := esper.try_component(targeting_ent, cmp.Spell):
            source = location.player_position()
            range_aoe = location.coords_within_radius(source, spell.target_range)
            for x, y in range_aoe:
                cell = cell_rgbs[x][y]
                glyph, fg, bg = cell[0], cell[1], cell[2]

                fg = display.brighter(fg, scale=100)
                if cell[0] in display.get_tile_glyphs():
                    fg = display.Color.BEIGE
                if bg not in (display.Color.LIGHT_RED, display.Color.BLOOD_RED):
                    # a poor subtitute for an "is there an aoe here" check
                    bg = display.Color.CANDLE

                cell_rgbs[x][y] = glyph, fg, bg

        for x, y in highlighted:
            cell = cell_rgbs[x][y]
            cell_rgbs[x][y] = cell[0], cell[1], display.Color.TARGET

        self.present(cell_rgbs)


@dataclass
class InventoryRender(BoardRender):
    context: tcod.context.Context
    console: tcod.console.Console

    def display_inventory(self):
        menu_selection = ecs.Query(cmp.MenuSelection, cmp.InventoryMenu).cmp(0)

        inv_map = create.player.inventory_map()
        for i, (name, entities) in enumerate(inv_map):
            text = f"{len(entities)}x {name}"
            fg = display.Color.WHITE
            bg = display.Color.BLACK
            if menu_selection.item == i:
                fg, bg = bg, fg
            self.console.print(1, 3 + i, string=text, fg=fg, bg=bg)

    def _process(self) -> None:
        self.console.clear()
        self._draw_panels()

        cell_rgbs = self._get_cell_rgbs()

        self.display_inventory()
        self.present(cell_rgbs)


@dataclass
class InventoryInputEvent(InputEvent):
    def __init__(self):
        to_level = (phase.change_to, [phase.Ontology.level])
        self.action_map = {
            input.KEYMAP[input.Input.MOVE_DOWN]: (self.move_selection, [1]),
            input.KEYMAP[input.Input.MOVE_UP]: (self.move_selection, [-1]),
            input.KEYMAP[input.Input.ESC]: to_level,
            input.KEYMAP[input.Input.SELECT]: self.handle_select,
        }

    def move_selection(self, diff: int):
        menu_selection = ecs.Query(cmp.MenuSelection, cmp.InventoryMenu).cmp(0)
        inventory_size = len(create.player.inventory_map()) - 1
        menu_selection.item += diff
        menu_selection.item = math_util.clamp(menu_selection.item, inventory_size)

    def handle_select(self):
        state = tcod.event.get_keyboard_state()
        alt_key = input.KEYMAP[input.Input.ALTERNATE]
        selection = get_selected_menuitem()
        if state[alt_key.scancode]:
            self.drop(selection)
            return
        self.use_item(selection)

    def drop(self, selection):
        esper.remove_component(selection, cmp.InInventory)
        player_pos = location.player_position()
        drop_pos = cmp.Position(x=player_pos.x, y=player_pos.y)
        esper.add_component(selection, drop_pos)

        board = location.get_board()
        board.entities_at(*drop_pos).add(selection)

        name = event.Log.color_fmt(selection)
        event.Log.append(f"dropped {name}")
        if not any(ecs.Query(cmp.InInventory)):
            phase.change_to(phase.Ontology.level)

    def use_item(self, selection):
        try:
            event.trigger_all_callbacks(selection, cmp.UseTrigger)
            esper.remove_component(selection, cmp.InInventory)
            event.Tick()
            phase.change_to(phase.Ontology.level, NPCEval)
        except typ.InvalidAction as e:
            esper.dispatch_event("flash")
            event.Log.append(str(e))


@dataclass
class OptionsRender(Render):
    context: tcod.context.Context
    console: tcod.console.Console

    def _process(self):
        self.console.clear()
        x = display.CENTER_W
        y = display.CENTER_H
        self.center_print(x, y, "OPTIONS")

        y_idx = itertools.count(y + 2)
        for k, v in input.KEYMAP.items():
            height = next(y_idx)
            self.right_print(x=x, y=height, string=f"{k.name}: ")
            self.left_print(x=x + 1, y=height, string=v.name)

        self.context.present(self.console)


@dataclass
class OptionsInputEvent(InputEvent):
    def __init__(self):
        self.action_map = {
            input.KEYMAP[input.Input.ESC]: (
                phase.change_to,
                [phase.Ontology.main_menu],
            ),
        }


@dataclass
class AboutRender(Render):
    context: tcod.context.Context
    console: tcod.console.Console

    def _process(self):
        self.console.clear()

        self.center_print(display.CENTER_W, display.CENTER_H, "ABOUT")

        about_text = [
            "placeholder text explaining lore and game mechanics",
            "second line",
        ]
        y_idx = itertools.count(display.CENTER_H + 1)
        for row in about_text:
            self.center_print(display.CENTER_W, next(y_idx), row)

        self.context.present(self.console)


@dataclass
class AboutInputEvent(InputEvent):
    def __init__(self):
        self.action_map = {
            input.KEYMAP[input.Input.ESC]: (
                phase.change_to,
                [phase.Ontology.main_menu],
            ),
        }


@dataclass
class Upkeep(Processor):
    """apply and tick down Conditions"""

    def _process(self) -> None:
        if not event.Queues.tick:
            return
        event.Queues.tick.clear()
        for entity, (status,) in ecs.Query(cmp.State):
            for status_effect, duration in list(status.map.items()):
                condition.apply(entity, status_effect, duration)
                status.map[status_effect] = max(0, duration - 1)
                if status.map[status_effect] == 0:
                    del status.map[status_effect]


@dataclass
class Animation(Processor):
    context: tcod.context.Context
    console: tcod.console.Console

    def flash_pos(self, coord, event):
        """change glyph at a position"""
        x, y = coord
        board_x = display.BOARD_STARTX + x
        board_y = display.BOARD_STARTY + y

        glyph, fg, bg = self.console.rgb[board_x, board_y]

        glyph = event.glyph or glyph
        fg = event.fg or fg
        bg = event.bg or bg

        in_fov = location.get_fov()
        if in_fov[x][y]:
            bg = location.backlight(x, y)

        self.console.rgb[board_x, board_y] = (glyph, fg, bg)

    def _process(self):
        max_len = max(len(anim.locs) for anim in event.Queues.animation)
        for idx in range(max_len):
            for anim in event.Queues.animation:
                if idx < len(anim.locs):
                    coord = anim.locs[idx]
                    self.flash_pos(coord, anim)

            self.context.present(self.console)
            time.sleep(0.07)  # display long enough to be seen
            esper.dispatch_event("redraw")

        event.Queues.animation.clear()


@dataclass
class Spawn(Processor):
    def _process(self):
        while event.Queues.spawn:
            spawn_event = event.Queues.spawn.popleft()
            spawn_event.func()

        board = location.get_board()
        board.build_entity_cache()
