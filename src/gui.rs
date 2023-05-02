use rltk::{Point, Rltk};
use specs::prelude::*;
use std::cmp::{max, min};

use crate::{Map, COLORS};

use super::map::{MAPHEIGHT, MAPWIDTH};
use super::{components, config, GameLog, Player, RunState, State};
pub use components::*;

// TODO: this shouldn't live here
pub const SCHOOLS: [&str; 3] = ["fireball", "magic_missile", "healing"];

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
pub enum ItemMenuResult {
    Cancel,
    NoResponse,
    Up,
    Down,
    Selected,
    Drop,
}

#[derive(PartialEq, Copy, Clone)]
pub enum SelectMenuResult {
    Cancel,
    NoResponse,
    Up,
    Down,
    Selected,
}

#[derive(PartialEq, Copy, Clone)]
pub enum SelectResult {
    Cancel,
    NoResponse,
    Selected,
}

pub fn draw_ui(ecs: &World, ctx: &mut Rltk) {
    ctx.draw_box(0, MAPHEIGHT, MAPWIDTH - 1, 6, COLORS.white, COLORS.black);

    let map = ecs.fetch::<Map>();
    let depth = format!("Depth: {}", map.depth);
    ctx.print_color(2, 43, COLORS.yellow, COLORS.black, &depth);

    let combat_stats = ecs.read_storage::<CombatStats>();
    let players = ecs.read_storage::<Player>();
    for (_player, stats) in (&players, &combat_stats).join() {
        let health = format!(" HP: {} / {} ", stats.hp, stats.max_hp);
        ctx.print_color(12, MAPWIDTH, COLORS.yellow, COLORS.black, &health);

        ctx.draw_bar_horizontal(
            28,
            MAPHEIGHT,
            51,
            stats.hp,
            stats.max_hp,
            COLORS.red,
            COLORS.black,
        );
    }
    let log = ecs.fetch::<GameLog>();

    let mut y = MAPHEIGHT + 1; // 44;
    for s in log.entries.iter().rev() {
        if y < MAPHEIGHT + 6 {
            // 49
            ctx.print(2, y, s);
        }
        y += 1;
    }
}

pub fn show_inventory(
    gs: &mut State,
    ctx: &mut Rltk,
    selection: usize,
) -> (ItemMenuResult, Option<Entity>) {
    let white = COLORS.white;
    let black = COLORS.black;
    let yellow = COLORS.yellow;
    let magenta = COLORS.magenta;

    let fgcolor = white;
    let bgcolor = black;
    let hlcolor = magenta;

    let player_entity = gs.ecs.fetch::<Entity>();
    let names = gs.ecs.read_storage::<Name>();
    let backpack = gs.ecs.read_storage::<InBackpack>();
    let entities = gs.ecs.entities();

    let inventory = (&backpack, &names, &entities)
        .join()
        .filter(|item| item.0.owner == *player_entity);

    let halfwidth = MAPWIDTH / 2;
    ctx.draw_box(0, 0, halfwidth, MAPHEIGHT, fgcolor, bgcolor);
    ctx.draw_box(halfwidth + 1, 0, halfwidth, MAPHEIGHT, fgcolor, bgcolor);
    ctx.print_color_centered(0, yellow, bgcolor, "Inventory");
    ctx.print_color_centered(MAPHEIGHT, yellow, bgcolor, "ESCAPE to cancel");

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

    let up = config::cfg_to_kc(&config::CONFIG.up);
    let down = config::cfg_to_kc(&config::CONFIG.down);
    let exit = config::cfg_to_kc(&config::CONFIG.exit);
    let drop = config::cfg_to_kc(&config::CONFIG.drop);
    let select = config::cfg_to_kc(&config::CONFIG.select);
    match ctx.key {
        None => (ItemMenuResult::NoResponse, None),
        Some(key) => match key {
            _ if key == exit => (ItemMenuResult::Cancel, None),
            _ if key == up => (ItemMenuResult::Up, None),
            _ if key == down => (ItemMenuResult::Down, None),
            _ if key == drop => (ItemMenuResult::Drop, Some(equippable[selection])),
            //TODO: below breaks if inventory is empty
            _ if key == select && selection < equippable.len() => {
                (ItemMenuResult::Selected, Some(equippable[selection]))
            }
            _ => (ItemMenuResult::NoResponse, None),
        },
    }
}

pub fn ranged_target(ecs: &mut World, ctx: &mut Rltk, range: i32) -> SelectResult {
    let player_entity = ecs.fetch::<Entity>();
    let player_pos = ecs.fetch::<Point>();
    let viewsheds = ecs.read_storage::<Viewshed>();
    let mut cursor = ecs.fetch_mut::<Cursor>();

    let yellow = COLORS.yellow;
    let black = COLORS.black;
    let cyan = COLORS.cyan;
    let red = COLORS.red;
    ctx.print_color(5, 0, yellow, black, "Select Target:");

    // Highlight available target cells
    let mut available_cells = Vec::new();
    let visible = viewsheds.get(*player_entity);
    if let Some(visible) = visible {
        // We have a viewshed
        for idx in visible.visible_tiles.iter() {
            let distance = rltk::DistanceAlg::Pythagoras.distance2d(*player_pos, *idx);
            if distance <= range as f32 {
                ctx.set_bg(idx.x, idx.y, COLORS.blue);
                available_cells.push(idx);
            }
        }
    } else {
        return SelectResult::Cancel;
    }

    let mut valid_target = false;
    for idx in available_cells.iter() {
        if idx.x == cursor.point.x && idx.y == cursor.point.y {
            valid_target = true;
        }
    }
    let mut curs_color = red;
    if valid_target {
        curs_color = cyan;
    }
    ctx.set_bg(cursor.point.x, cursor.point.y, curs_color);
    // TODO: if there is an AOE, highlight that too

    let up = config::cfg_to_kc(&config::CONFIG.up);
    let down = config::cfg_to_kc(&config::CONFIG.down);
    let left = config::cfg_to_kc(&config::CONFIG.left);
    let right = config::cfg_to_kc(&config::CONFIG.right);
    let exit = config::cfg_to_kc(&config::CONFIG.exit);
    let select = config::cfg_to_kc(&config::CONFIG.select);

    match ctx.key {
        None => SelectResult::NoResponse,
        Some(key) => match key {
            _ if key == exit => SelectResult::Cancel,
            //TODO: bounds checking
            _ if key == up => {
                cursor.point.y -= 1;
                SelectResult::NoResponse
            }
            _ if key == down => {
                cursor.point.y += 1;
                SelectResult::NoResponse
            }
            _ if key == left => {
                cursor.point.x -= 1;
                SelectResult::NoResponse
            }
            _ if key == right => {
                cursor.point.x += 1;
                SelectResult::NoResponse
            }
            _ if key == select => SelectResult::Selected,
            _ => SelectResult::NoResponse,
        },
    }
}

// TODO: this is really close to the inventory one, might be able to dry it up
pub fn chargen_menu(
    _gs: &mut State,
    ctx: &mut Rltk,
    selection: usize,
) -> (SelectMenuResult, Option<usize>) {
    let white = COLORS.white;
    let black = COLORS.black;
    let yellow = COLORS.yellow;
    let magenta = COLORS.magenta;

    let fgcolor = white;
    let bgcolor = black;
    let hlcolor = magenta;

    let halfwidth = MAPWIDTH / 2;
    ctx.draw_box(0, 0, halfwidth, MAPHEIGHT, fgcolor, bgcolor);
    ctx.draw_box(halfwidth + 1, 0, halfwidth, MAPHEIGHT, fgcolor, bgcolor);
    ctx.print_color_centered(0, yellow, black, "Choose a spell school");

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

    let up = config::cfg_to_kc(&config::CONFIG.up);
    let down = config::cfg_to_kc(&config::CONFIG.down);
    let exit = config::cfg_to_kc(&config::CONFIG.exit);
    let select = config::cfg_to_kc(&config::CONFIG.select);
    match ctx.key {
        None => (SelectMenuResult::NoResponse, None),
        Some(key) => match key {
            _ if key == exit => (SelectMenuResult::Cancel, None),
            _ if key == up => (SelectMenuResult::Up, None),
            _ if key == down => (SelectMenuResult::Down, None),
            _ if key == select => (SelectMenuResult::Selected, Some(selection)),
            _ => (SelectMenuResult::NoResponse, None),
        },
    }
}

pub fn main_menu(gs: &mut State, ctx: &mut Rltk) -> MainMenuResult {
    let runstate = gs.ecs.fetch::<RunState>();

    let white = COLORS.white;
    let yellow = COLORS.yellow;
    let black = COLORS.black;
    let magenta = COLORS.magenta;

    ctx.print_color_centered(15, yellow, black, "Malefactor");

    let states = [
        MainMenuSelection::NewGame,
        MainMenuSelection::Continue,
        MainMenuSelection::Quit,
    ];

    let mut idx: i8;
    let state_num: i8 = states.len() as i8;

    if let RunState::MainMenu {
        menu_selection: selection,
    } = *runstate
    {
        let mut ngcolor = white;
        let mut lgcolor = white;
        let mut qcolor = white;
        match selection {
            MainMenuSelection::NewGame => {
                ngcolor = magenta;
                idx = 0;
            }
            MainMenuSelection::Continue => {
                lgcolor = magenta;
                idx = 1;
            }
            MainMenuSelection::Quit => {
                qcolor = magenta;
                idx = 2;
            }
        }

        ctx.print_color_centered(24, ngcolor, black, "Begin New Game");
        ctx.print_color_centered(25, lgcolor, black, "Continue");
        ctx.print_color_centered(26, qcolor, black, "Quit");

        let down = config::cfg_to_kc(&config::CONFIG.down);
        let up = config::cfg_to_kc(&config::CONFIG.up);
        let exit = config::cfg_to_kc(&config::CONFIG.exit);
        let select = config::cfg_to_kc(&config::CONFIG.select);
        match ctx.key {
            None => {
                return MainMenuResult::NoSelection {
                    selected: selection,
                }
            }
            Some(key) => match key {
                _ if key == exit => {
                    return MainMenuResult::NoSelection {
                        selected: MainMenuSelection::Quit,
                        // TODO: here we can continue. maybe?
                        // Alternatively there would need to be a continue button
                    };
                }
                _ if key == up => {
                    idx = max(0, idx - 1);
                    return MainMenuResult::NoSelection {
                        selected: states[idx as usize],
                    };
                }
                _ if key == down => {
                    idx = min(state_num - 1, idx + 1);
                    return MainMenuResult::NoSelection {
                        selected: states[idx as usize],
                    };
                }
                _ if key == select => {
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
