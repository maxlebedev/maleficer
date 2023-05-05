use std::collections::HashMap;

use super::rect::Rect;
use super::{components, CombatStats, Name, Player, Position, Renderable, Viewshed, COLORS};
use crate::map;
use crate::raws::{get_spawn_table_for_depth, spawn_named_entity, SpawnType, RAWS};
use crate::systems::random_table::RandomTable;
use rltk::RandomNumberGenerator;
use specs::prelude::*;
use specs::saveload::SimpleMarker;

pub use components::*;
use specs::saveload::MarkedBuilder;

const MAX_SPAWNS: i32 = 4;

/// Fills a room with stuff!
#[allow(clippy::map_entry)]
pub fn spawn_room(ecs: &mut World, room: &Rect, depth: i32) {
    let spawn_table = room_table(depth);
    let mut spawn_points: HashMap<usize, String> = HashMap::new();

    // Scope to keep the borrow checker happy
    {
        let mut rng = ecs.write_resource::<RandomNumberGenerator>();
        let num_spawns = rng.roll_dice(1, MAX_SPAWNS + 3) - 3;

        for _i in 0..num_spawns {
            let mut added = false;
            let mut tries = 0;
            // We try to resolve collisions 20x
            while !added && tries < 20 {
                let x = (room.x1 + rng.roll_dice(1, i32::abs(room.x2 - room.x1))) as usize;
                let y = (room.y1 + rng.roll_dice(1, i32::abs(room.y2 - room.y1))) as usize;
                let idx = (y * map::MAPWIDTH) + x;
                if !spawn_points.contains_key(&idx) {
                    spawn_points.insert(idx, spawn_table.roll(&mut rng));
                    added = true;
                } else {
                    tries += 1;
                }
            }
        }
    }

    for spawn in spawn_points.iter() {
        let x = (*spawn.0 % map::MAPWIDTH) as i32;
        let y = (*spawn.0 / map::MAPWIDTH) as i32;

        spawn_named_entity(
            &RAWS.lock().unwrap(),
            ecs.create_entity(),
            spawn.1,
            SpawnType::AtPosition { x, y },
        );
    }
}

pub fn player(ecs: &mut World, player_x: i32, player_y: i32) -> Entity {
    ecs.create_entity()
        .with(Position {
            x: player_x,
            y: player_y,
        })
        .with(Renderable {
            glyph: rltk::to_cp437('@'),
            fg: COLORS.yellow,
            bg: COLORS.black,
            render_order: 0,
        })
        .with(Player {})
        .with(Viewshed {
            visible_tiles: Vec::new(),
            range: 8,
            dirty: true,
        })
        .with(Name {
            name: "Player".to_string(),
        })
        .with(CombatStats {
            max_hp: 30,
            hp: 30,
            defense: 2,
            power: 5,
        })
        .marked::<SimpleMarker<SerializeMe>>()
        .build()
}

fn room_table(depth: i32) -> RandomTable {
    get_spawn_table_for_depth(&RAWS.lock().unwrap(), depth)
}
