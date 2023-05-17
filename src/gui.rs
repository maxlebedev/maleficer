use rltk::{Point, Rltk};
use specs::prelude::*;

use crate::config::{CONFIG, INPUT};
use crate::{camera, Map, COLORS};

use super::{components, GameLog, Player, RunState, State};
pub use components::*;

// TODO: this shouldn't live here
pub const SCHOOLS: [&str; 3] = [
    "unimplemented spells school 1",
    "unimplemented spells school 2",
    "unimplemented spells school 3",
];

#[derive(PartialEq, Copy, Clone)]
pub enum MainMenuSelection {
    NewGame,
    Continue,
    Quit,
}

#[derive(PartialEq, Copy, Clone)]
pub enum MainMenuResult {
    NoSelection { selected: MainMenuSelection },
    Selected { selected: MainMenuSelection },
}

#[derive(PartialEq, Copy, Clone)]
pub enum MenuAction {
    Cancel,
    NoResponse,
    Up,
    Down,
    Selected,
    Drop,
}

pub fn draw_ui(ecs: &World, ctx: &mut Rltk) {
    let ui_height = 7;
    let height = CONFIG.height - ui_height;
    let width = CONFIG.width;
    ctx.draw_box(0, height, width - 1, 6, COLORS.white, COLORS.black);

    let map = ecs.fetch::<Map>();
    let depth = format!("Depth: {}", map.depth);
    ctx.print_color(2, height, COLORS.yellow, COLORS.black, &depth);

    // TODO: consider removing this for release?
    let point = ecs.fetch::<Point>();
    let coords = format!("Player Coords: {}:{}", point.x, point.y);
    ctx.print_color(25, height, COLORS.yellow, COLORS.black, &coords);

    let combat_stats = ecs.read_storage::<CombatStats>();
    let players = ecs.read_storage::<Player>();
    for (_player, stats) in (&players, &combat_stats).join() {
        let health = format!(" HP: {} / {} ", stats.hp, stats.max_hp);
        ctx.print_color(12, height, COLORS.yellow, COLORS.black, &health);

        let hp_bar_left = width / 3; // was 28
        let hp_bar_right = (width / 3) * 2; // was 51
        ctx.draw_bar_horizontal(
            hp_bar_left,
            height,
            hp_bar_right,
            stats.hp,
            stats.max_hp,
            COLORS.red,
            COLORS.black,
        );
    }
    let log = ecs.fetch::<GameLog>();

    let mut y = height + 1; // 44;
    for s in log.entries.iter().rev() {
        if y < height + ui_height -1 {
            ctx.print(2, y, s);
        }
        y += 1;
    }
}

pub fn show_inventory(
    gs: &mut State,
    ctx: &mut Rltk,
    selection: usize,
) -> (MenuAction, Option<Entity>) {
    let fgcolor = COLORS.white;
    let bgcolor = COLORS.black;
    let hlcolor = COLORS.magenta;

    let player_entity = gs.ecs.fetch::<Entity>();
    let names = gs.ecs.read_storage::<Name>();
    let backpack = gs.ecs.read_storage::<InBackpack>();
    let entities = gs.ecs.entities();

    let ui_height = 7;
    let height = CONFIG.height - ui_height;
    let width = CONFIG.width;

    let inventory = (&backpack, &names, &entities)
        .join()
        .filter(|item| item.0.owner == *player_entity);

    let halfwidth = width / 2;
    ctx.draw_box(0, 0, halfwidth, height, fgcolor, bgcolor);
    ctx.draw_box(halfwidth + 1, 0, halfwidth, height, fgcolor, bgcolor);
    ctx.print_color_centered(0, COLORS.yellow, bgcolor, "Inventory");
    ctx.print_color_centered(height, COLORS.yellow, bgcolor, "ESCAPE to cancel");

    let inv_offset = 2;
    let mut equippable: Vec<Entity> = Vec::new();
    for (y, item) in inventory.enumerate() {
        let mut color = fgcolor;
        if y == selection {
            color = hlcolor;
        }
        ctx.print_color(
            inv_offset,
            y + inv_offset,
            color,
            bgcolor,
            &item.1.name.to_string(),
        );
        equippable.push(item.2);
    }

    match ctx.key {
        None => (MenuAction::NoResponse, None),
        Some(key) => match key {
            _ if key == INPUT.exit => (MenuAction::Cancel, None),
            _ if key == INPUT.up && selection > 0 => (MenuAction::Up, None),
            _ if key == INPUT.down && selection < equippable.len() - 1 => (MenuAction::Down, None),
            _ if key == INPUT.drop => (MenuAction::Drop, Some(equippable[selection])),
            _ if key == INPUT.select && selection < equippable.len() => {
                (MenuAction::Selected, Some(equippable[selection]))
            }
            _ => (MenuAction::NoResponse, None),
        },
    }
}

pub fn ranged_target(ecs: &mut World, ctx: &mut Rltk, range: i32, radius: i32) -> MenuAction {
    let player_entity = ecs.fetch::<Entity>();
    let player_pos = ecs.fetch::<Point>();
    let viewsheds = ecs.read_storage::<Viewshed>();
    let mut cursor = ecs.fetch_mut::<Cursor>();

    ctx.print_color(5, 0, COLORS.yellow, COLORS.black, "Select Target:");

    // Highlight available target cells
    let mut available_cells = Vec::new();
    let visible = viewsheds.get(*player_entity);
    if let Some(visible) = visible {
        // We have a viewshed
        for idx in visible.visible_tiles.iter() {
            let distance = rltk::DistanceAlg::Pythagoras.distance2d(*player_pos, *idx);
            if distance <= range as f32 && camera::in_screen_bounds(ecs, idx.x, idx.y) {
                let screen_pt = camera::tile_to_screen(ecs, *idx);
                ctx.set_bg(screen_pt.x, screen_pt.y, COLORS.blue);
                available_cells.push(*idx);
            }
        }
    } else {
        return MenuAction::Cancel;
    }

    let mut valid_target = false;
    for idx in available_cells.iter() {
        let scr_pt = camera::tile_to_screen(ecs, *idx);
        if scr_pt.x == cursor.point.x && scr_pt.y == cursor.point.y {
            valid_target = true;
        }
    }
    let mut curs_color = COLORS.red;
    if valid_target {
        curs_color = COLORS.cyan;
    }
    ctx.set_bg(cursor.point.x, cursor.point.y, curs_color);
    let blast_tiles = camera::screen_fov(ecs, cursor.point, radius);
    for tile in blast_tiles.iter() {
        if *tile == cursor.point {
            continue;
        }
        ctx.set_bg(tile.x, tile.y, COLORS.dark_grey);
    }

    match ctx.key {
        None => MenuAction::NoResponse,
        Some(key) => match key {
            _ if key == INPUT.exit => MenuAction::Cancel,
            //TODO: bounds checking
            _ if key == INPUT.up => {
                cursor.point.y -= 1;
                MenuAction::NoResponse
            }
            _ if key == INPUT.down => {
                cursor.point.y += 1;
                MenuAction::NoResponse
            }
            _ if key == INPUT.left => {
                cursor.point.x -= 1;
                MenuAction::NoResponse
            }
            _ if key == INPUT.right => {
                cursor.point.x += 1;
                MenuAction::NoResponse
            }
            _ if key == INPUT.select => MenuAction::Selected,
            _ => MenuAction::NoResponse,
        },
    }
}

// TODO: this is really close to the inventory one, might be able to dry it up
pub fn chargen_menu(
    _gs: &mut State,
    ctx: &mut Rltk,
    selection: usize,
) -> (MenuAction, Option<usize>) {
    let fgcolor = COLORS.white;
    let bgcolor = COLORS.black;
    let hlcolor = COLORS.magenta;

    let ui_height = 7;
    let height = CONFIG.height - ui_height;
    let width = CONFIG.width;

    let halfwidth = width / 2;
    ctx.draw_box(0, 0, halfwidth, height, fgcolor, bgcolor);
    ctx.draw_box(halfwidth + 1, 0, halfwidth - 1, height, fgcolor, bgcolor);
    ctx.print_color_centered(0, COLORS.yellow, COLORS.black, "Choose a spell school");

    let inv_offset = 2;
    for (y, school) in SCHOOLS.iter().enumerate() {
        let mut color = fgcolor;
        if y == selection {
            color = hlcolor;
        }
        ctx.print_color(
            inv_offset,
            y + inv_offset,
            color,
            bgcolor,
            &school.to_string(),
        );
    }

    match ctx.key {
        None => (MenuAction::NoResponse, None),
        Some(key) => match key {
            _ if key == INPUT.exit => (MenuAction::Cancel, None),
            _ if key == INPUT.up && selection > 0 => (MenuAction::Up, None),
            _ if key == INPUT.down && selection < SCHOOLS.len() - 1 => (MenuAction::Down, None),
            _ if key == INPUT.select => (MenuAction::Selected, Some(selection)),
            _ => (MenuAction::NoResponse, None),
        },
    }
}

pub fn main_menu(gs: &mut State, ctx: &mut Rltk) -> MainMenuResult {
    let runstate = gs.ecs.fetch::<RunState>();

    ctx.print_color_centered(15, COLORS.yellow, COLORS.black, "Malefactor");

    let states = [
        MainMenuSelection::NewGame,
        MainMenuSelection::Continue,
        MainMenuSelection::Quit,
    ];

    let idx: usize;
    let state_num = states.len();

    if let RunState::MainMenu {
        game_started: _,
        menu_selection: selection,
    } = *runstate
    {
        let mut ngcolor = COLORS.white;
        let mut lgcolor = COLORS.white;
        let mut qcolor = COLORS.white;
        match selection {
            MainMenuSelection::NewGame => {
                ngcolor = COLORS.magenta;
                idx = 0;
            }
            MainMenuSelection::Continue => {
                lgcolor = COLORS.magenta;
                idx = 1;
            }
            MainMenuSelection::Quit => {
                qcolor = COLORS.magenta;
                idx = 2;
            }
        }

        ctx.print_color_centered(24, ngcolor, COLORS.black, "Begin New Game");
        ctx.print_color_centered(25, lgcolor, COLORS.black, "Continue");
        ctx.print_color_centered(26, qcolor, COLORS.black, "Quit");

        match ctx.key {
            None => {
                return MainMenuResult::NoSelection {
                    selected: selection,
                }
            }
            Some(key) => match key {
                _ if key == INPUT.exit => {
                    return MainMenuResult::NoSelection {
                        selected: MainMenuSelection::Quit,
                        // TODO: here we can continue. maybe?
                        // Alternatively there would need to be a continue button
                    };
                }
                _ if key == INPUT.up && idx > 0 => {
                    return MainMenuResult::NoSelection {
                        selected: states[idx - 1],
                    };
                }
                _ if key == INPUT.down && idx < state_num - 1 => {
                    return MainMenuResult::NoSelection {
                        selected: states[idx + 1],
                    };
                }
                _ if key == INPUT.select => {
                    return MainMenuResult::Selected {
                        selected: selection,
                    }
                }
                _ => {
                    return MainMenuResult::NoSelection {
                        selected: selection,
                    }
                }
            },
        }
    }

    MainMenuResult::NoSelection {
        selected: MainMenuSelection::NewGame,
    }
}
