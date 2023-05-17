use crate::{config::CONFIG, COLORS};
use specs::prelude::*;

use super::{Hidden, Map, Position, Renderable, TileType};
use rltk::{Point, Rltk, RGB};

const SHOW_BOUNDARIES: bool = true;

// TODO: memoize?
pub fn get_screen_bounds(ecs: &World) -> (i32, i32, i32, i32) {
    let player_pos = ecs.fetch::<Point>();

    let center_x = (CONFIG.width / 2) as i32;
    let center_y = (CONFIG.height / 2) as i32;

    let min_x = player_pos.x - center_x;
    let max_x = min_x + CONFIG.width as i32;
    let min_y = player_pos.y - center_y;
    let max_y = min_y + CONFIG.height as i32;

    (min_x, max_x, min_y, max_y)
}

pub fn tile_to_screen(ecs: &World, tile: Point) -> Point {
    let player_pos = ecs.fetch::<Point>();

    let center_x = (CONFIG.width / 2) as i32;
    let center_y = (CONFIG.height / 2) as i32;

    let min_x = player_pos.x - center_x;
    let min_y = player_pos.y - center_y;

    let x = tile.x - min_x;
    let y = tile.y - min_y;

    rltk::Point { x, y }
}

pub fn screen_to_tile(ecs: &World, point: Point) -> Point {
    let player_pos = ecs.fetch::<Point>();

    let center_x = (CONFIG.width / 2) as i32;
    let center_y = (CONFIG.height / 2) as i32;

    let min_x = player_pos.x - center_x;
    let min_y = player_pos.y - center_y;

    let x = point.x + min_x;
    let y = point.y + min_y;
    rltk::Point { x, y }
}

pub fn in_screen_bounds(ecs: &World, x: i32, y: i32) -> bool {
    let tile = Point { x, y };
    let screen_pt = tile_to_screen(ecs, tile);

    if screen_pt.x > 1
        && screen_pt.x < CONFIG.width as i32 - 1
        && screen_pt.y > 1
        && screen_pt.y < CONFIG.height as i32 - 1
    {
        return true;
    }
    return false;
}

pub fn screen_fov(ecs: &World, screen_pt: Point, radius: i32) -> Vec<Point> {
    let curs_tile = screen_to_tile(ecs, screen_pt);
    let map = ecs.fetch::<Map>();
    let blast_tiles = rltk::field_of_view(curs_tile, radius, &*map);
    // let mut ret = Vec::<Point>::new();
    blast_tiles
        .iter()
        .map(|x| tile_to_screen(ecs, *x))
        .collect()
}

pub fn render_camera(ecs: &World, ctx: &mut Rltk) {
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
                    ctx.set(x, y, fg, bg, glyph);
                }
            } else if SHOW_BOUNDARIES {
                ctx.set(x, y, COLORS.grey, COLORS.black, rltk::to_cp437('+'));
            }
        }
    }

    let positions = ecs.read_storage::<Position>();
    let renderables = ecs.read_storage::<Renderable>();
    let hidden = ecs.read_storage::<Hidden>();
    let map = ecs.fetch::<Map>();

    let mut data = (&positions, &renderables, !&hidden)
        .join()
        .collect::<Vec<_>>();
    data.sort_by(|&a, &b| b.1.render_order.cmp(&a.1.render_order));
    for (pos, render, _hidden) in data.iter() {
        let idx = map.xy_idx(pos.x, pos.y);
        if map.visible_tiles[idx] && in_screen_bounds(ecs, pos.x, pos.y) {
            let screen_pt = tile_to_screen(ecs, rltk::Point { x: pos.x, y: pos.y });
            ctx.set(screen_pt.x, screen_pt.y, render.fg, render.bg, render.glyph);
        }
    }
}

fn get_tile_glyph(idx: usize, map: &Map) -> (rltk::FontCharType, RGB, RGB) {
    let glyph;
    let mut fg;
    let bg = COLORS.black;

    match map.tiles[idx] {
        TileType::Floor => {
            glyph = rltk::to_cp437('.');
            fg = COLORS.dark_cyan;
        }
        TileType::Wall => {
            let x = idx as i32 % map.width;
            let y = idx as i32 / map.width;
            glyph = wall_glyph(&map, x, y);
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

// is the guard here on total tiles, or on window dimentions?
fn is_revealed_and_wall(map: &Map, x: i32, y: i32) -> bool {
    let idx = map.xy_idx(x, y);
    if idx >= map.tile_count {
        false;
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

#[cfg(test)]
mod tests {
    use crate::{camera::*, State};

    #[test]
    fn test_get_screen_bounds() {
        let (player_x, player_y) = (20, 15);
        let mut state = State { ecs: World::new() };
        state.ecs.insert(Point::new(player_x, player_y));
        let (min_x, max_x, min_y, max_y) = get_screen_bounds(&state.ecs);
        // these are relative to CONFIG.height/width
        assert_eq!(min_x, -70);
        assert_eq!(max_x, 110);

        assert_eq!(min_y, -45);
        assert_eq!(max_y, 75);
    }
}
