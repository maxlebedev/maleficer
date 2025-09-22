import itertools
from dataclasses import dataclass
from functools import partial

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
import phase
import typ


def get_selected_menuitem():
    # TODO: move somewhere
    inv_map = create.player.inventory_map()
    menu_selection = ecs.Query(cmp.MenuSelection).val
    selection = inv_map[menu_selection.item][1].pop()
    return selection


@dataclass
class Movement(esper.Processor):
    def bump(self, source, target):
        """one entity bumps into another"""
        src_is_enemy = esper.has_components(source, cmp.Enemy, cmp.Melee)
        target_is_harmable = esper.has_component(target, cmp.Health)
        target_is_enemy = esper.has_component(target, cmp.Enemy)
        if src_is_enemy and target_is_harmable and not target_is_enemy:
            esper.add_component(source, cmp.Target(target=target))
            event.trigger_all_callbacks(source, cmp.EnemyTrigger)

        if esper.has_component(source, cmp.Player):
            # Note: walking into a wall consumes a turn
            event.Log.append("can't move there")
            esper.dispatch_event("flash")

    def pick_up(self, target):
        """pick up an item"""
        board = location.get_board()
        board.remove(target)
        esper.add_component(target, cmp.InInventory())
        create.player.inventory_map()
        name = esper.component_for_entity(target, cmp.Onymous).name
        event.Log.append(f"player picked up {name}")
        # oneshot call some collectable processor?

    def process(self):
        board = location.get_board()
        while event.Queues.movement:
            movement = event.Queues.movement.popleft()  # left so player first
            mover = movement.source
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
class Damage(esper.Processor):
    def _make_message(self, source: str, target: str, amount: int):
        if amount > 0:
            return f"{source} deals {amount} to {target}"
        return f"{source} heals {-1 * amount} to {target}"

    def process(self):
        board = location.get_board()
        while event.Queues.damage:
            damage = event.Queues.damage.popleft()
            if not esper.entity_exists(damage.target):
                # if entity doesn't exist anymore, damage fizzles
                continue
            if esper.has_component(damage.target, cmp.Cell):
                pos = esper.component_for_entity(damage.target, cmp.Position)
                entities = board.pieces_at(pos)
                for ent in entities:
                    if esper.has_component(ent, cmp.Health):
                        event.Damage(damage.source, ent, damage.amount)
            if not esper.has_component(damage.target, cmp.Health):
                # damage source hit a wall, or similar
                continue

            math_util.clamp_damage(damage.target, damage.amount)

            to_name = lambda x: esper.component_for_entity(x, cmp.Onymous).name
            src_name = damage.source[cmp.Onymous].name
            target_name = f"{to_name(damage.target)}#{damage.target}"

            message = self._make_message(src_name, target_name, damage.amount)

            if cmp.Position not in damage.source or location.in_player_perception(
                damage.source[cmp.Position]
            ):
                event.Log.append(message)

            """
            hp = esper.component_for_entity(damage.target, cmp.Health)
            if hp.current <= 0:
                event.Death(damage.target)
                phase.oneshot(Death)
            """


@dataclass
class Death(esper.Processor):
    def queue_zero_health(self):
        for ent, (hp,) in ecs.Query(cmp.Health):
            if hp.current <= 0:
                cmps = esper.components_for_entity(ent)
                print(f"{ent=} {cmps}")
                event.Death(ent)

    def process(self):
        board = location.get_board()

        self.queue_zero_health()
        while event.Queues.death:
            killable = event.Queues.death.popleft().entity
            if not esper.entity_exists(killable):
                continue
            named = esper.component_for_entity(killable, cmp.Onymous)

            pos = esper.component_for_entity(killable, cmp.Position)
            if killable_cell := board.get_cell(*pos):
                esper.add_component(killable, cmp.Target(target=killable_cell))
                event.trigger_all_callbacks(killable, cmp.DeathTrigger)
            if location.in_player_perception(pos):
                message = f"{named.name}#{killable} is no more"
                event.Log.append(message)
            if esper.has_component(killable, cmp.Cell):
                floor = create.tile.floor(pos.x, pos.y)
                board.set_cell(pos.x, pos.y, floor)
                board.build_entity_cache()
            else:
                board.remove(killable)
                esper.delete_entity(killable, immediate=True)
            self.queue_zero_health()


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

        menu_selection = ecs.Query(cmp.MenuSelection).val
        menu_selection.item = 0
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
        for spell_ent, (known) in esper.get_component(cmp.Known):
            if known.slot == slot:
                esper.remove_component(spell_ent, cmp.Known)
                scroll = create.item.scroll(spell=spell_ent)
                esper.add_component(scroll, cmp.InInventory())
                unlearned = True
                event.Tick()
                phase.change_to(phase.Ontology.level, NPCTurn)
        if not unlearned:
            esper.dispatch_event("flash")
            event.Log.append("can't unlearn, spell doesn't exist")

    def to_target(self, slot: int):
        # TODO: This probably wants to take spell_ent and not slot num
        board = location.get_board()

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
        board.reposition(xhair_ent, *player_pos)
        esper.add_component(casting_spell, cmp.Targeting())
        phase.change_to(phase.Ontology.target)


@dataclass
class NPCTurn(esper.Processor):
    def follow(self, start: cmp.Position, end: cmp.Position):
        board = location.get_board()
        cost = board.as_move_graph()
        graph = tcod.path.SimpleGraph(cost=cost, cardinal=1, diagonal=0)
        pf = tcod.path.Pathfinder(graph)
        pf.add_root(start.as_tuple)
        path: list = pf.path_to(end.as_tuple).tolist()
        if len(path) < 2:
            return None
        return path[1]

    def process_ranged(self, entity: int, epos: cmp.Position):
        player_pos = location.player_last_position()
        enemy_cmp = esper.component_for_entity(entity, cmp.Enemy)
        # TODO: ranged units should also sometimes follow
        player = ecs.Query(cmp.Player).first()
        if location.can_see(entity, player, enemy_cmp.perception):
            if condition.has(entity, typ.Condition.Cooldown):
                behavior.wander(entity)
            else:
                event.trigger_all_callbacks(entity, cmp.EnemyTrigger)
        else:
            if condition.has(entity, typ.Condition.Cooldown):
                # on cooldown, so player was close enough to follow them
                if move := self.follow(epos, player_pos):
                    event.Movement(entity, x=move[0], y=move[1])
            else:
                behavior.wander(entity)

    def process_melee(self, entity: int, epos: cmp.Position):
        player_pos = location.player_last_position()
        if player_pos.as_tuple == epos.as_tuple:
            player_pos = location.player_position()
        enemy_cmp = esper.component_for_entity(entity, cmp.Enemy)
        dist_to_player = location.euclidean_distance(player_pos, epos)
        if dist_to_player > enemy_cmp.perception:
            behavior.wander(entity)
        else:
            if move := self.follow(epos, player_pos):
                event.Movement(entity, x=move[0], y=move[1])

    def process(self):
        # some of this probably want so live in behavior.py
        stunned = set()

        enemies = ecs.Query(cmp.Enemy)
        for entity, _ in enemies:
            if condition.has(entity, typ.Condition.Stun):
                stunned.add(entity)

        for entity in stunned:
            name = esper.component_for_entity(entity, cmp.Onymous).name
            event.Log.append(f"{name} is stunned")

        for entity, _ in enemies.filter(cmp.Wander).remove(stunned):
            behavior.wander(entity)

        melee_enemies = enemies.filter(cmp.Melee, cmp.Position).remove(stunned)
        for entity, (_, epos) in melee_enemies:
            enemy = esper.component_for_entity(entity, cmp.Enemy)
            self.process_melee(entity, epos)
            for _ in range(1, enemy.speed):
                phase.oneshot(Movement)
                self.process_melee(entity, epos)

        archers = enemies.filter(cmp.Ranged, cmp.Position).remove(stunned)
        for entity, (_, epos) in archers:
            self.process_ranged(entity, epos)

        set_behavior = (cmp.Ranged, cmp.Melee, cmp.Wander)
        enemies = ecs.Query(cmp.Enemy)
        others = enemies.exclude(*set_behavior).remove(stunned)
        for entity, (_) in others:
            event.trigger_all_callbacks(entity, cmp.EnemyTrigger)


@dataclass
class Render(esper.Processor):
    context: tcod.context.Context
    console: tcod.console.Console

    dashes = "─" * (display.PANEL_WIDTH - 2)

    def left_print(self, *args, **kwargs):
        self.console.print(alignment=libtcodpy.LEFT, *args, **kwargs)

    def center_print(self, *args, **kwargs):
        self.console.print(alignment=libtcodpy.CENTER, *args, **kwargs)

    def right_print(self, *args, **kwargs):
        self.console.print(alignment=libtcodpy.RIGHT, *args, **kwargs)

    def present(self, cell_rgbs):
        startx, endx = (display.PANEL_WIDTH, display.R_PANEL_START)
        starty, endy = (0, display.BOARD_HEIGHT)
        self.console.rgb[startx:endx, starty:endy] = cell_rgbs
        # TODO if the magnification changes, the above line breaks
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
        self.console.print(x=x, y=y, string=text, fg=display.Color.DGREY)

    def _draw_selection_info(self, entity: int):
        selection_info = []
        spell_component_details = [
            ("Damage", cmp.DamageEffect, "amount"),
            ("Heal", cmp.HealEffect, "amount"),
            ("Range", cmp.Spell, "target_range"),
            ("Cooldown", cmp.Cooldown, "turns"),
        ]
        for name, try_cmp, attr in spell_component_details:
            if component := esper.try_component(entity, try_cmp):
                value = getattr(component, attr)
                selection_info.append(f"{name}:{value}")
        if bleed_effect := esper.try_component(entity, cmp.BleedEffect):
            message = f"Grants Bleed:{bleed_effect.value}"
            selection_info.append(message)
        if push := esper.try_component(entity, cmp.PushEffect):
            message = f"Imposes Push:{push.distance}"
            selection_info.append(message)
        if stun_effect := esper.try_component(entity, cmp.StunEffect):
            message = f"Grants Stun:{stun_effect.value}"
            selection_info.append(message)
        if aoe := esper.try_component(entity, cmp.EffectArea):
            # callback kwargs into spell info
            # this may not be right for other callbacks
            for name, value in aoe.callback.keywords.items():
                message = f"{name.title()}:{value}"
                selection_info.append(message)
        return selection_info

    def _spell_section(self):
        spells = ecs.Query(cmp.Spell, cmp.Onymous, cmp.Known)
        sorted_spells = sorted(spells, key=lambda x: x[1][2].slot)

        for spell_ent, (_, named, known) in sorted_spells:
            text = f"Slot{known.slot}:{named.name}"
            if cd := condition.get_val(spell_ent, typ.Condition.Cooldown):
                text = f"{text}:{typ.Condition.Cooldown.name} {cd}"
            fg = display.Color.WHITE
            bg = display.Color.BLACK
            if esper.has_component(spell_ent, cmp.Targeting):
                fg, bg = bg, fg
            yield (text, fg, bg)

    def _right_panel(self, panel_params):
        self.console.draw_frame(x=display.R_PANEL_START, **panel_params)
        for i, message in enumerate(event.Log.messages):
            self.console.print(1 + display.R_PANEL_START, 1 + i, message)

    def _left_panel(self, panel_params):
        self.console.draw_frame(x=0, **panel_params)
        hp = ecs.Query(cmp.Player, cmp.Health).cmp(cmp.Health)
        self.render_bar(1, 1, hp.current, hp.max, display.PANEL_WIDTH - 2)

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

        panel_contents = []

        panel_contents += self._inventory()
        panel_contents.append(self.dashes)

        panel_contents += self._spell_section()
        panel_contents.append(self.dashes)

        # if targeting, also print spell info

        if targeting := esper.get_component(cmp.Targeting):
            trg_ent, _ = targeting[0]
            panel_contents += self._draw_selection_info(trg_ent)
        else:
            if phase.CURRENT == phase.Ontology.inventory:
                selection = get_selected_menuitem()
                if learnable := esper.try_component(selection, cmp.Learnable):
                    panel_contents += self._draw_selection_info(learnable.spell)
                else:
                    panel_contents += self._draw_selection_info(selection)

        for y_idx, content in enumerate(panel_contents, start=3):
            match content:
                case str():
                    self.console.print(1, y_idx, content)
                case tuple():
                    self.console.print(1, y_idx, *content)

        for i, cnd in enumerate(self.gather_conditions()):
            y = display.BOARD_HEIGHT - i - 2
            self.console.print(1, y, cnd, fg=display.Color.LEMON)

    def gather_conditions(self):
        ret = []
        for _, (cnd_state, _) in ecs.Query(cmp.State, cmp.Player):
            for status_effect, duration in cnd_state.map.items():
                # triggers 3x/turn for some reason?
                ret.append(f"{status_effect} {duration}")
        return ret

    def _apply_lighting(self, cell_rgbs, in_fov) -> list[list[typ.CELL_RGB]]:
        """display cells in fov with lighting, explored without, and hide the rest"""
        board = location.get_board()
        # for screenshots, debugging
        # for cell in board.as_sequence():
        # location.Board.explored.add(cell)
        for x, col in enumerate(cell_rgbs):
            for y, (glyph, fgcolor, _) in enumerate(col):
                cell = board.get_cell(x, y)
                if not cell:
                    continue
                if in_fov[x][y]:
                    board.explored.add(cell)

                    if phase.CURRENT != phase.Ontology.target:
                        brighter = display.brighter(fgcolor, scale=100)
                        cell_rgbs[x][y] = (glyph, brighter, display.Color.CANDLE)
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

        aura_ents = ecs.Query(cmp.Position, cmp.Aura)
        for _, (pos, aura) in aura_ents:
            aura_cells = aura.callback(pos)
            for x, y in aura_cells:
                if not in_fov[x][y]:
                    continue
                cell = cell_rgbs[x][y]
                cell_rgbs[x][y] = cell[0], cell[1], aura.color

        return cell_rgbs

    def process(self):
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
    background: display.BGImage | None = None

    def process(self):
        self.console.clear()
        x = display.PANEL_WIDTH + (display.BOARD_WIDTH // 2)
        y = display.BOARD_HEIGHT // 2
        self.console.print(x, y, self.title, alignment=libtcodpy.CENTER)

        menu_selection = ecs.Query(cmp.MenuSelection).val

        menu_elements = ecs.Query(cmp.MenuItem, self.menu_cmp, cmp.Onymous)
        sorted_menu = sorted(menu_elements, key=lambda x: x[1][0].order)
        for i, (_, (mi, _, on)) in enumerate(sorted_menu):
            fg = display.Color.LGREY
            if menu_selection.item == mi.order:
                fg = display.Color.WHITE
            self.center_print(x=x, y=y + 2 + i, string=on.name, fg=fg)

        if self.background:
            display.blit_image(
                self.console, self.background.obj, scale=self.background.scale
            )

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
        menu_selection = ecs.Query(cmp.MenuSelection).val
        for entity, (mi, _) in ecs.Query(cmp.MenuItem, self.menu_cmp):
            if mi.order == menu_selection.item:
                event.trigger_all_callbacks(entity, cmp.UseTrigger)

    def move_selection(self, diff: int):
        menu_selection = ecs.Query(cmp.MenuSelection).val
        menu_selection.item += diff

        tot_items = len([_ for _ in ecs.Query(cmp.MenuItem, self.menu_cmp)]) - 1
        menu_selection.item = math_util.clamp(menu_selection.item, tot_items)


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
        phase.change_to(phase.Ontology.level)

    def move_crosshair(self, x, y):
        crosshair = ecs.Query(cmp.Crosshair, cmp.Position).first()
        pos = ecs.cmps[crosshair][cmp.Position]

        # TODO: maybe break out range to its own cmp and check for it here
        spell_cmp = ecs.Query(cmp.Spell, cmp.Targeting).cmp(cmp.Spell)

        player_pos = location.player_position()
        new_pos = cmp.Position(pos.x + x, pos.y + y)
        dist_to_player = location.euclidean_distance(player_pos, new_pos)
        if not spell_cmp or dist_to_player <= spell_cmp.target_range:
            event.Movement(crosshair, x, y, relative=True)

    def select(self):
        xhair_pos = ecs.Query(cmp.Crosshair, cmp.Position).cmp(cmp.Position)
        targeting_entity = ecs.Query(cmp.Targeting).first()
        board = location.get_board()

        if not esper.has_component(targeting_entity, cmp.Target):
            cell = xhair_pos.lookup_in(board.cells)
            trg = cmp.Target(target=cell)
            esper.add_component(targeting_entity, trg)

        try:
            event.trigger_all_callbacks(targeting_entity, cmp.UseTrigger)
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

    def process(self) -> None:
        self.console.clear()
        self._draw_panels()

        cell_rgbs = self._get_cell_rgbs()

        targeting_ent = ecs.Query(cmp.Targeting).first()
        pos = ecs.Query(cmp.Crosshair).cmp(cmp.Position)
        highlighted = [[pos.x, pos.y]]

        if aoe := esper.try_component(targeting_ent, cmp.EffectArea):
            highlighted += aoe.callback(pos)

        if spell := esper.try_component(targeting_ent, cmp.Spell):
            source = location.player_position()
            range_aoe = location.coords_within_radius(source, spell.target_range)
            for x, y in range_aoe:
                cell = cell_rgbs[x][y]
                glyph, fg, bg = cell[0], cell[1], cell[2]

                bg = display.Color.CANDLE
                fg = display.brighter(fg, scale=100)
                repaintable = (
                    display.Glyph.FLOOR,
                    display.Glyph.WALL,
                    display.Glyph.BWALL,
                )
                if cell[0] in repaintable:
                    fg = display.Color.BEIGE
                if cell[0] == display.Glyph.NONE:
                    bg = display.brighter(bg, scale=25)

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
        menu_selection = ecs.Query(cmp.MenuSelection).val

        inv_map = create.player.inventory_map()
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
        to_level = (phase.change_to, [phase.Ontology.level])
        self.action_map = {
            input.KEYMAP[input.Input.MOVE_DOWN]: (self.move_selection, [1]),
            input.KEYMAP[input.Input.MOVE_UP]: (self.move_selection, [-1]),
            input.KEYMAP[input.Input.ESC]: to_level,
            input.KEYMAP[input.Input.SELECT]: self.handle_select,
        }

    def move_selection(self, diff: int):
        menu_selection = ecs.Query(cmp.MenuSelection).val
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
        board.entities_at(drop_pos).add(selection)
        phase.change_to(phase.Ontology.level, NPCTurn)

    def use_item(self, selection):
        try:
            event.trigger_all_callbacks(selection, cmp.UseTrigger)
            esper.remove_component(selection, cmp.InInventory)
            event.Tick()
            phase.change_to(phase.Ontology.level, NPCTurn)
        except typ.InvalidAction as e:
            esper.dispatch_event("flash")
            event.Log.append(str(e))


@dataclass
class OptionsRender(Render):
    context: tcod.context.Context
    console: tcod.console.Console

    def process(self):
        self.console.clear()
        x = display.PANEL_WIDTH + (display.BOARD_WIDTH // 2)
        y = display.BOARD_HEIGHT // 2
        self.console.print(x, y, "OPTIONS", alignment=libtcodpy.CENTER)

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

    def process(self):
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
