use std::cmp::min;
use std::collections::HashMap;

use itertools::Itertools;
use rltk::{Point, Rltk, RGB, to_cp437};
use specs::prelude::*;

use crate::config::{BOUNDS, INPUT};
use crate::{camera, Map, COLORS};

use super::{components, GameLog, Player, RunState, State};
pub use components::*;

// TODO: this shouldn't live here
pub const SCHOOLS: [&str; 3] = [
    "unimplemented magical discipline 1",
    "unimplemented magical discipline 2",
    "unimplemented magical discipline 3",
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
}

pub fn draw_horizontal_line(
    ctx: &mut Rltk,
    sx: i32,
    sy: i32,
    width: i32,
    fg: RGB,
    bg: RGB,
    ends: bool,
) {
    for x in 0..width {
        ctx.set(sx + x, sy, fg, bg, rltk::to_cp437('─'));
    }
    if ends {
        ctx.set(sx, sy, fg, bg, rltk::to_cp437('├'));
        ctx.set(sx + width, sy, fg, bg, rltk::to_cp437('┤'));
    }
}

fn count_strings(strings: Vec<&String>) -> Vec<String> {
    let mut counts: HashMap<&String, usize> = HashMap::new();

    for string in strings {
        *counts.entry(string).or_insert(0) += 1;
    }

    let result: Vec<String> = counts
        .iter()
        .sorted_by(|a, b| Ord::cmp(&a, &b))
        .map(|(&string, &count)| format!("{} {}", count, string))
        .collect();
    result
}

pub const UI_WIDTH: usize = 40;

fn draw_resource_bar(ctx: &mut Rltk, stats: &EntityStats, resource_name: &str, x: i32, y: i32, color: RGB){

    let (current, max) = stats.get(resource_name);
    let health = format!("{}:{}/{} ", resource_name, current, max);
    ctx.print_color(
        x,
        y,
        COLORS.yellow,
        COLORS.black,
        &health,
    );

    let bar_left = health.len();
    let bar_right = UI_WIDTH  - 1 - bar_left;

    // ctx.draw_bar_horizontal isn't empty at 0%, so we make our own
    let percent = current as f32 / max as f32;
    let fill_width = (percent * bar_right as f32) as usize;
    for x in 0..bar_right{
        let glyph;
        if x < fill_width {
             glyph = '▓';
        } else {
            glyph = '░';
        }
        ctx.set(bar_left + x, y, color, COLORS.black, to_cp437(glyph));
    }
}

pub fn draw_char_ui(ecs: &World, ctx: &mut Rltk) {
    // Sidebar with sections
    // Char info
    // Hotkeys
    // Status Effects
    // Inventory
    let ui_height = BOUNDS.win_height;
    let ui_start_x = 0;
    let ui_start_y = 0;
    let ui_width = UI_WIDTH - 1; // the inside
    ctx.draw_box(
        ui_start_x,
        ui_start_y,
        ui_width,
        ui_height,
        COLORS.white,
        COLORS.black,
    );

    let combat_stats = ecs.read_storage::<EntityStats>();
    let players = ecs.read_storage::<Player>();
    for (_player, stats) in (&players, &combat_stats).join() {
        draw_resource_bar(ctx, stats, "hit_points", ui_start_x+1, ui_start_y+1, COLORS.red);
        draw_resource_bar(ctx, stats, "mana", ui_start_x+1, ui_start_y+2, COLORS.cyan);
    }

    //inventory
    let player_entity = ecs.fetch::<Entity>();
    let names = ecs.read_storage::<Name>();
    let backpack = ecs.read_storage::<InBackpack>();
    let entities = ecs.entities();
    let inventory = (&backpack, &names, &entities)
        .join()
        .sorted_by(|a, b| Ord::cmp(&a.1.name, &b.1.name))
        .filter(|item| item.0.owner == *player_entity);

    draw_horizontal_line(
        ctx,
        ui_start_x,
        19,
        ui_width as i32,
        COLORS.white,
        COLORS.black,
        true,
    );

    let inventory_start = 20;

    let just_names: Vec<&String> = inventory.into_iter().map(|el| &el.1.name).collect();
    let distinct_counts = count_strings(just_names);

    for (y, item) in distinct_counts.iter().enumerate() {
        ctx.print_color(
            ui_start_x + 1,
            y + inventory_start,
            COLORS.white,
            COLORS.black,
            &item.to_string(),
        );
    }
}

pub fn draw_world_ui(ecs: &World, ctx: &mut Rltk) {
    // Sidebar with sections
    // Depth
    // cursor tile description
    // Log
    let ui_height = BOUNDS.win_height;
    let ui_width = UI_WIDTH - 1;
    let ui_start_x = BOUNDS.win_width - UI_WIDTH;
    let ui_start_y = 0;
    ctx.draw_box(
        ui_start_x,
        ui_start_y,
        ui_width,
        ui_height,
        COLORS.white,
        COLORS.black,
    );
    let map = ecs.fetch::<Map>();
    let depth = format!("Depth: {}", map.depth);
    ctx.print_color(ui_start_x + 1, 1, COLORS.yellow, COLORS.black, &depth);

    let history = 20;
    let log = ecs.fetch::<GameLog>();
    let log_start = ui_height - min(history, log.entries.len()) - 1;

    let to_print = log
        .entries
        .iter()
        .rev()
        .flat_map(|s| wrap_text(s, UI_WIDTH - 2));
    let mut y = log_start;
    for s in to_print {
        if y < ui_height - 1 {
            ctx.print(ui_start_x + 1, y, s);
        }
        y += 1;
    }
}

fn wrap_text(text: &str, max_width: usize) -> Vec<String> {
    text.chars()
        .chunks(max_width)
        .into_iter()
        .map(|chunk| chunk.collect::<String>())
        .collect::<Vec<String>>()
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
                camera::set_bg_view(ctx, screen_pt.x, screen_pt.y, COLORS.blue);
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
    camera::set_bg_view(ctx, cursor.point.x, cursor.point.y, curs_color);
    let blast_tiles = camera::blast_tiles(ecs, cursor.point, radius);
    for tile in blast_tiles.iter() {
        if *tile == cursor.point {
            continue;
        }
        camera::set_bg_view(ctx, tile.x, tile.y, COLORS.dark_grey);
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
            _ if key == INPUT.select && valid_target => MenuAction::Selected,
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

    let height = BOUNDS.win_height;
    let width = BOUNDS.win_width;

    let halfwidth = width / 2;
    ctx.draw_box(0, 0, halfwidth, height, fgcolor, bgcolor);
    ctx.draw_box(halfwidth + 1, 0, halfwidth - 1, height, fgcolor, bgcolor);
    ctx.print_color_centered(0, COLORS.yellow, COLORS.black, "Choose a magical discipline");

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

    ctx.print_color_centered(15, COLORS.yellow, COLORS.black, "Maleficer");

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
