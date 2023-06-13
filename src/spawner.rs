use std::collections::HashMap;

use super::rect::Rect;
use super::{components, EntityStats, Name, Player, Position, Renderable, Viewshed, COLORS};
use crate::raws::{get_spawn_table_for_depth, spawn_named_entity, SpawnType, RAWS};
use crate::systems::random_table::RandomTable;
use crate::Map;
use rltk::RandomNumberGenerator;
use specs::prelude::*;
use specs::saveload::SimpleMarker;

use super::map_builders::common::in_bounds;
pub use components::*;
use specs::saveload::MarkedBuilder;

const MAX_SPAWNS: i32 = 4;

pub fn spawn_room(ecs: &mut World, room: &Rect, map_depth: i32) {
    let mut possible_targets: Vec<usize> = Vec::new();
    {
        // Borrow scope - to keep access to the map separated
        let map = ecs.fetch::<Map>();
        for y in room.y1 + 1..room.y2 {
            for x in room.x1 + 1..room.x2 {
                let idx = map.xy_idx(x, y);
                if in_bounds(&map, idx) {
                    possible_targets.push(idx);
                }
            }
        }
    }

    spawn_region(ecs, &possible_targets, map_depth);
}

/// Fills a region with stuff!
pub fn spawn_region(ecs: &mut World, area: &[usize], map_depth: i32) {
    let spawn_table = room_table(map_depth);
    let mut spawn_points: HashMap<usize, String> = HashMap::new();
    let mut areas: Vec<usize> = Vec::from(area);

    // Scope to keep the borrow checker happy
    {
        let mut rng = ecs.write_resource::<RandomNumberGenerator>();
        let num_spawns = i32::min(
            areas.len() as i32,
            rng.roll_dice(1, MAX_SPAWNS + 3) + (map_depth - 1) - 1,
        );
        if num_spawns == 0 {
            return;
        }

        for _i in 0..num_spawns {
            let array_index = if areas.len() == 1 {
                0usize
            } else {
                (rng.roll_dice(1, areas.len() as i32) - 1) as usize
            };

            let map_idx = areas[array_index];
            spawn_points.insert(map_idx, spawn_table.roll(&mut rng));
            areas.remove(array_index);
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
        .with(EntityStats {
            defense: 2,
            power: 5,
            pools: HashMap::from([
                (
                    "hit_points".to_string(),
                    Pool {
                        max: 30,
                        current: 30,
                    },
                ),
                (
                    "mana".to_string(),
                    Pool {
                        max: 10,
                        current: 10,
                    },
                ),
            ]),
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
