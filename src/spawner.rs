use std::collections::HashMap;

use super::rect::Rect;
use super::{components, CombatStats, Name, Player, Position, Renderable, Viewshed, COLORS};
use crate::Map;
use crate::raws::{get_spawn_table_for_depth, spawn_named_entity, SpawnType, RAWS};
use crate::systems::random_table::RandomTable;
use rltk::RandomNumberGenerator;
use specs::prelude::*;
use specs::saveload::SimpleMarker;

pub use components::*;
use specs::saveload::MarkedBuilder;

const MAX_SPAWNS: i32 = 4;

#[allow(clippy::map_entry)]
pub fn spawn_room(ecs: &mut World, room: &Rect, depth: i32) {
    let spawn_table = room_table(depth);
    let mut spawn_points: HashMap<usize, String> = HashMap::new();

    // Scope to keep the borrow checker happy
    {
        let mut rng = ecs.write_resource::<RandomNumberGenerator>();
        let num_spawns = rng.roll_dice(1, MAX_SPAWNS + 3) - 3;
        let map = ecs.fetch::<Map>();

        for _i in 0..num_spawns {
            let mut added = false;
            let mut tries = 0;
            // We try to resolve collisions 20x
            while !added && tries < 20 {
                let x = room.x1 + rng.roll_dice(1, i32::abs(room.x2 - room.x1));
                let y = room.y1 + rng.roll_dice(1, i32::abs(room.y2 - room.y1));
                let idx = map.xy_idx(x, y);
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
        let (x, y);
        {
            let map = ecs.fetch::<Map>();
            (x, y) = map.idx_xy(*spawn.0);
        }

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

#[cfg(test)]
mod tests {
    use super::spawn_room;
    use crate::*;

    #[test]
    fn test_room() {
        // TODO: this goes in a setup function
        let mut test_state = State { ecs: World::new() };
        test_state.ecs.insert(rltk::RandomNumberGenerator::new());
        test_state.ecs.register::<Renderable>();

        let map = Map::new(1, 64, 64);
        test_state.ecs.insert(map);

        let new_room = rect::Rect::new(1, 1, 10, 10);
        let depth = 0;
        for _i in 0..100 {
            spawn_room(&mut test_state.ecs, &new_room, depth);
        }

        let num_ent = test_state.ecs.entities().join().count();

        assert!(num_ent < 500);
        assert!(num_ent > 0);
    }
}
