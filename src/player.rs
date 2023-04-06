use rltk::{VirtualKeyCode, Rltk};
use specs::prelude::*;
use super::{components, State, map};
use num;


const MAX_X: i32 = 80;
const MAX_Y: i32 = 50;

fn try_move_player(delta_x: i32, delta_y: i32, ecs: &mut World) {
    let mut positions = ecs.write_storage::<components::Position>();
    let mut players = ecs.write_storage::<components::Player>();
    let the_map = ecs.fetch::<Vec<map::TileType>>(); 
    // TODO: we are fetching by type exclusively. how? what if there were multiple maps

    for (_player, pos) in (&mut players, &mut positions).join() {
        let destination_idx = map::xy_idx(pos.x + delta_x, pos.y + delta_y);
        if the_map[destination_idx] != map::TileType::Wall {
            pos.x = num::clamp(pos.x + delta_x, 0, MAX_X-1);
            pos.y = num::clamp(pos.y + delta_y, 0, MAX_Y-1);
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
