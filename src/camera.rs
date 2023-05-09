use specs::prelude::*;
use crate::COLORS;

use super::{Map,TileType,Position,Renderable, Hidden};
use rltk::{Point, Rltk, RGB};

const SHOW_BOUNDARIES : bool = true;


pub fn get_screen_bounds(ecs: &World, ctx : &mut Rltk) -> (i32, i32, i32, i32) {
    let player_pos = ecs.fetch::<Point>();
    let (x_chars, y_chars) = ctx.get_char_size();

    let center_x = (x_chars / 2) as i32;
    let center_y = (y_chars / 2) as i32;

    let min_x = player_pos.x - center_x;
    let max_x = min_x + x_chars as i32;
    let min_y = player_pos.y - center_y;
    let max_y = min_y + y_chars as i32;

    (min_x, max_x, min_y, max_y)
}

pub fn in_screen_bounds(ecs: &World, ctx : &mut Rltk, x: i32, y: i32) -> bool{
    let (min_x, max_x, min_y, max_y) = get_screen_bounds(ecs, ctx);
    let screen_x = x - min_x;
    let screen_y = y - min_y;

    if screen_x > 1 && screen_x < (max_x - min_x)-1 && screen_y > 1 && screen_y < (max_y - min_y)-1 {
        return true;
    }
    return false;
}

pub fn render_camera(ecs: &World, ctx : &mut Rltk) {
    let map = ecs.fetch::<Map>();
    let (min_x, max_x, min_y, max_y) = get_screen_bounds(ecs, ctx);

    let map_width = map.width-1;
    let map_height = map.height-1;

    let mut y = 0;
    for ty in min_y .. max_y {
        let mut x = 0;
        for tx in min_x .. max_x {
            if tx > 0 && tx < map_width && ty > 0 && ty < map_height {
                let idx = map.xy_idx(tx, ty);
                if map.revealed_tiles[idx] {
                    let (glyph, fg, bg) = get_tile_glyph(idx, &*map);
                    ctx.set(x, y, fg, bg, glyph);
                }
            } else if SHOW_BOUNDARIES {
                ctx.set(x, y, COLORS.grey, COLORS.black, rltk::to_cp437('·'));
            }
            x += 1;
        }
        y += 1;
    }

    let positions = ecs.read_storage::<Position>();
    let renderables = ecs.read_storage::<Renderable>();
    let hidden = ecs.read_storage::<Hidden>();
    let map = ecs.fetch::<Map>();

    let mut data = (&positions, &renderables, !&hidden).join().collect::<Vec<_>>();
    data.sort_by(|&a, &b| b.1.render_order.cmp(&a.1.render_order) );
    for (pos, render, _hidden) in data.iter() {
        let idx = map.xy_idx(pos.x, pos.y);
        if map.visible_tiles[idx] { 
            let entity_screen_x = pos.x - min_x;
            let entity_screen_y = pos.y - min_y;
            if entity_screen_x > 0 && entity_screen_x < map_width && entity_screen_y > 0 && entity_screen_y < map_height {
                ctx.set(entity_screen_x, entity_screen_y, render.fg, render.bg, render.glyph);
            }
        }
    }
}

fn get_tile_glyph(idx: usize, map : &Map) -> (rltk::FontCharType, RGB, RGB) {
    let glyph;
    let mut fg;
    let mut bg = COLORS.black;

    match map.tiles[idx] {
        TileType::Floor => {
            glyph = rltk::to_cp437('.');
            fg = COLORS.dark_cyan;
        }
        TileType::Wall => {
            let x = idx as i32 % map.width;
            let y = idx as i32 / map.width;
            glyph = wall_glyph(&*map, x, y);
            fg = COLORS.green;
        }
        TileType::DownStairs => {
            glyph = rltk::to_cp437('▼');
            fg = COLORS.dark_cyan;
        }
    }
    if !map.visible_tiles[idx] { 
        fg = fg.to_greyscale();
    }

    (glyph, fg, bg)
}



pub const MAPWIDTH: usize = 80;
pub const MAPHEIGHT: usize = 43;
pub const MAPCOUNT: usize = MAPHEIGHT * MAPWIDTH;

fn is_revealed_and_wall(map: &Map, x: i32, y: i32) -> bool {
    let idx = map.xy_idx(x, y);
    if idx >= MAPCOUNT {
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

    match mask {
        0 => 254,  // ■ Pillar because we can't see neighbors
        1 => 186,  // ║ Wall only to the north
        2 => 186,  // ║ Wall only to the south
        3 => 186,  // ║ Wall to the north and south
        4 => 205,  // ═ Wall only to the west
        5 => 188,  // ╝ Wall to the north and west
        6 => 187,  // ╗ Wall to the south and west
        7 => 185,  // ╣ Wall to the north, south and west
        8 => 205,  // ═ Wall only to the east
        9 => 200,  // ╚ Wall to the north and east
        10 => 201, // ╔ Wall to the south and east
        11 => 204, // ╠ Wall to the north, south and east
        12 => 205, // ═ Wall to the east and west
        13 => 202, // ╩ Wall to the east, west, and south
        14 => 203, // ╦ Wall to the east, west, and north
        15 => 206, // ╬ Wall on all sides
        _ => 35,   // # We missed one?
    }
}

// TOOD: currently broken
// * can't deal damage to enemies
