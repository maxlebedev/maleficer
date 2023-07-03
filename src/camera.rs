use crate::{config::BOUNDS, gui::UI_WIDTH};
use specs::prelude::*;

use super::{Hidden, Map, Position, Renderable, TileType};
use rltk::{Point, Rltk, RGB};
use crate::to_rgb;

use bevy::prelude::{Color, Query, Without};

const SHOW_BOUNDARIES: bool = true;

// TODO: memoize?
pub fn get_screen_bounds(ecs: &World) -> (i32, i32, i32, i32) {
    let player_pos = ecs.fetch::<Point>();

    let center_x = (BOUNDS.view_width / 2) as i32;
    let center_y = (BOUNDS.view_height / 2) as i32;

    let min_x = player_pos.x - center_x;
    let max_x = min_x + BOUNDS.view_width as i32;
    let min_y = player_pos.y - center_y;
    let max_y = min_y + BOUNDS.view_height as i32;

    (min_x, max_x, min_y, max_y)
}

pub fn tile_to_screen(player_pos: Point, tile: Point) -> Point {
    let center_x = (BOUNDS.view_width / 2) as i32;
    let center_y = (BOUNDS.view_height / 2) as i32;

    let min_x = player_pos.x - center_x;
    let min_y = player_pos.y - center_y;

    let x = tile.x - min_x;
    let y = tile.y - min_y;

    rltk::Point { x, y }
}

pub fn screen_to_tile(player_pos: Point, point: Point) -> Point {
    let center_x = (BOUNDS.view_width / 2) as i32;
    let center_y = (BOUNDS.view_height / 2) as i32;

    let min_x = player_pos.x - center_x;
    let min_y = player_pos.y - center_y;

    let x = point.x + min_x;
    let y = point.y + min_y;
    rltk::Point { x, y }
}

pub fn in_screen_bounds(player_pos: Point, x: i32, y: i32) -> bool {
    let tile = Point { x, y };
    let screen_pt = tile_to_screen(player_pos, tile);

    if screen_pt.x > 1
        && screen_pt.x < BOUNDS.view_width as i32 - 1
        && screen_pt.y > 1
        && screen_pt.y < BOUNDS.view_height as i32 - 1
    {
        return true;
    }
    false
}

pub fn blast_tiles(ecs: &World, screen_pt: Point, radius: i32) -> Vec<Point> {
    let player_pos = ecs.fetch::<Point>();
    let curs_tile = screen_to_tile(*player_pos, screen_pt);
    let map = ecs.fetch::<Map>();
    let blast_tiles = rltk::field_of_view(curs_tile, radius, &*map);
    // let mut ret = Vec::<Point>::new();
    blast_tiles
        .iter()
        .map(|x| tile_to_screen(*player_pos, *x))
        .collect()
}

pub fn set_view(ctx: &mut Rltk, x: i32, y: i32, fg: RGB, bg: RGB, glyph: u16) {
    // there's a thing where we can specify x,y are types that convert to usize, but idk how to do that yet
    ctx.set(x + UI_WIDTH as i32, y, fg, bg, glyph);
}

pub fn set_bg_view(ctx: &mut Rltk, x: i32, y: i32, bg: RGB) {
    let ui_width = UI_WIDTH as i32;
    ctx.set_bg(x + ui_width, y, bg);
}

pub fn render_camera(ecs: &World,
    renderables: Query<(&Position, &Renderable, Without<Hidden>)>,
    ctx: &mut Rltk) {
    let map = ecs.fetch::<Map>();
    let (min_x, max_x, min_y, max_y) = get_screen_bounds(ecs);

    let map_width = map.width - 1;
    let map_height = map.height - 1;

    for (y, ty) in (min_y..max_y).enumerate() {
        for (x, tx) in (min_x..max_x).enumerate() {
            if tx > 0 && tx < map_width && ty > 0 && ty < map_height {
                let idx = map.xy_idx(tx, ty);
                if map.revealed_tiles[idx] {
                    let (glyph, fg, bg) = get_tile_glyph(idx, &map);
                    set_view(ctx, x as i32, y as i32, fg, bg, glyph);
                }
            } else if SHOW_BOUNDARIES {
                set_view(
                    ctx,
                    x as i32,
                    y as i32,
                    to_rgb(Color::GRAY),
                    to_rgb(Color::BLACK),
                    rltk::to_cp437('+'),
                );
            }
        }
    }

    let positions = ecs.read_storage::<Position>();
    let renderables = ecs.read_storage::<Renderable>();
    let hidden = ecs.read_storage::<Hidden>();
    let map = ecs.fetch::<Map>();

    let mut data = renderables.iter_mut();
    //(&positions, &renderables, !&hidden) .join() .collect::<Vec<_>>();
    data.sort_by(|&a, &b| b.1.render_order.cmp(&a.1.render_order));
    for (pos, render, _hidden) in data.iter() {
        let idx = map.xy_idx(pos.x, pos.y);
        if map.visible_tiles[idx] && in_screen_bounds(ecs, pos.x, pos.y) {
            let screen_pt = tile_to_screen(ecs, rltk::Point { x: pos.x, y: pos.y });
            set_view(
                ctx,
                screen_pt.x,
                screen_pt.y,
                render.fg,
                render.bg,
                render.glyph,
            );
        }
    }
}

fn get_tile_glyph(idx: usize, map: &Map) -> (rltk::FontCharType, RGB, RGB) {
    let glyph;
    let mut fg;
    let mut bg = to_rgb(Color::BLACK);

    match map.tiles[idx] {
        TileType::Floor => {
            glyph = rltk::to_cp437('.');
            fg = to_rgb(Color::MIDNIGHT_BLUE);
        }
        TileType::Wall => {
            let (x,y) = map.idx_xy(idx as i32);
            glyph = wall_glyph(map, x, y);
            fg = to_rgb(Color::GREEN);
        }
        TileType::DownStairs => {
            glyph = rltk::to_cp437('▼');
            fg = to_rgb(Color::MIDNIGHT_BLUE);
        }
    }
    if !map.visible_tiles[idx] {
        fg = fg.to_greyscale();
    }

    if map.bloodstains.contains(&idx) {
        bg = to_rgb(Color::CRIMSON);
        // maybe change floor tiles to this? '▓'
    }

    (glyph, fg, bg)
}

// is the guard here on total tiles, or on window dimentions?
fn is_revealed_and_wall(map: &Map, x: i32, y: i32) -> bool {
    let idx = map.xy_idx(x, y);
    if idx >= map.tile_count {
        return false;
    }
    map.tiles[idx] == TileType::Wall && map.revealed_tiles[idx]
}
fn wall_glyph(map: &Map, x: i32, y: i32) -> rltk::FontCharType {
    let mut mask: u8 = 0;

    if is_revealed_and_wall(map, x, y - 1) {
        mask += 1;
    }
    if is_revealed_and_wall(map, x, y + 1) {
        mask += 2;
    }
    if is_revealed_and_wall(map, x - 1, y) {
        mask += 4;
    }
    if is_revealed_and_wall(map, x + 1, y) {
        mask += 8;
    }

    let mut diag: u8 = 0;

    if is_revealed_and_wall(map, x - 1, y - 1) {
        diag += 1;
    }
    if is_revealed_and_wall(map, x - 1, y + 1) {
        diag += 2;
    }
    if is_revealed_and_wall(map, x + 1, y - 1) {
        diag += 4;
    }
    if is_revealed_and_wall(map, x + 1, y + 1) {
        diag += 8;
    }

    match mask {
        0 => rltk::to_cp437('■'), // ■ Pillar because we can't see neighbors
        1 => rltk::to_cp437('║'), // ║ Wall only to the north
        2 => rltk::to_cp437('║'), // ║ Wall only to the south
        3 => rltk::to_cp437('║'), // ║ Wall to the north and south
        4 => rltk::to_cp437('═'), // ═ Wall only to the west
        5 => rltk::to_cp437('╝'), // ╝ Wall to the north and west
        6 => rltk::to_cp437('╗'), // ╗ Wall to the south and west
        7 => match diag {
            3 | 6 | 7 | 9 | 11 => rltk::to_cp437('║'),
            _ => rltk::to_cp437('╣'), // ╣ Wall to the north, south and west
        },
        8 => rltk::to_cp437('═'),  // ═ Wall only to the east
        9 => rltk::to_cp437('╚'),  // ╚ Wall to the north and east
        10 => rltk::to_cp437('╔'), // ╔ Wall to the south and east
        11 => match diag {
            6 | 9 | 12 | 13 | 14 => rltk::to_cp437('║'),
            _ => rltk::to_cp437('╠'), // ╠ Wall to the north, south and east
        },
        12 => rltk::to_cp437('═'), // ═ Wall to the east and west
        13 => match diag {
            5 | 6 | 7 | 9 | 10 | 13 => rltk::to_cp437('═'),
            _ => rltk::to_cp437('╩'), // ╦ Wall to the east, west, and north
        },
        14 => match diag {
            6 | 9 | 10 | 11 | 14 => rltk::to_cp437('═'),
            _ => rltk::to_cp437('╦'), // ╦ Wall to the east, west, and south
        },
        15 => rltk::to_cp437('╬'),
        _ => rltk::to_cp437('#'), // # We missed one?
    }
}
