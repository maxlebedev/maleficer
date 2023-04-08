use rltk::{VirtualKeyCode, Rltk};
use specs::prelude::*;
use super::{components, State, map};
use num;

fn try_move_player(delta_x: i32, delta_y: i32, ecs: &mut World) {
    let mut positions = ecs.write_storage::<components::Position>();
    let mut players = ecs.write_storage::<components::Player>();
    let mut viewsheds = ecs.write_storage::<components::Viewshed>();
    let map = ecs.fetch::<map::Map>();
    // TODO: we are fetching by type exclusively. how? what if there were multiple maps

    for (_player, pos, viewshed) in (&mut players, &mut positions, &mut viewsheds).join() {
        let destination_idx = map.xy_idx(pos.x + delta_x, pos.y + delta_y);
        if map.tiles[destination_idx] != map::TileType::Wall {
            pos.x = num::clamp(pos.x + delta_x, 0, map.width-1);
            pos.y = num::clamp(pos.y + delta_y, 0, map.height-1);
            viewshed.dirty = true;
        }
    }
}

pub fn player_input(gs: &mut State, ctx: &mut Rltk) {
    // Player movement
    match ctx.key {
        None => {} // Nothing happened
        Some(key) => match key {
            VirtualKeyCode::Left => try_move_player(-1, 0, &mut gs.ecs),
            VirtualKeyCode::Right => try_move_player(1, 0, &mut gs.ecs),
            VirtualKeyCode::Up => try_move_player(0, -1, &mut gs.ecs),
            VirtualKeyCode::Down => try_move_player(0, 1, &mut gs.ecs),
            _ => {}
        },
    }
}
