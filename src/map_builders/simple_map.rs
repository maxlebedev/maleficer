use crate::Position;
use crate::TileType;
use crate::rect::Rect;
use crate::spawner;

use super::MapBuilder;
use super::Map;
use super::common::*;
use rltk::RandomNumberGenerator;
use specs::World;


pub struct SimpleMapBuilder {}

impl MapBuilder for SimpleMapBuilder {

    fn build_map(&mut self, new_depth: i32, width: i32, height: i32) -> (Map, Position) {
        let mut map = Map::new(new_depth, width, height);
        let playerpos = SimpleMapBuilder::rooms_and_corridors(&mut map);
        (map, playerpos)
    }

    fn spawn_entities(&mut self, map : &Map, ecs : &mut World) {
        for room in map.rooms.iter().skip(1) {
            spawner::spawn_room(ecs, room, map.depth);
        }
    }

}

impl SimpleMapBuilder {

    pub fn new() -> SimpleMapBuilder {
        SimpleMapBuilder {}
    }

    /// Makes a new map using the algorithm from http://rogueliketutorials.com/tutorials/tcod/part-3/
    /// This gives a handful of random rooms and corridors joining them together.
    pub fn rooms_and_corridors(map: &mut Map) -> Position{
        const MAX_ROOMS: i32 = 30;
        const MIN_SIZE: i32 = 6;
        const MAX_SIZE: i32 = 10;

        let mut rng = RandomNumberGenerator::new();

        for _ in 0..MAX_ROOMS {
            let w = rng.range(MIN_SIZE, MAX_SIZE);
            let h = rng.range(MIN_SIZE, MAX_SIZE);
            let x = rng.range(1, map.width - w - 1);
            let y = rng.range(1, map.height - h - 1);
            let new_room = Rect::new(x, y, w, h);
            let mut ok = true;
            for other_room in map.rooms.iter() {
                if new_room.intersect(other_room) {
                    // TODO: I think this is broken, but I might perfer intersections
                    ok = false
                }
            }
            if ok {
                apply_room_to_map(map, &new_room);
                if !map.rooms.is_empty() {
                    let (new_x, new_y) = new_room.center();
                    let (prev_x, prev_y) = map.rooms[map.rooms.len() - 1].center();
                    // prev is the most recent one, not the closest one
                    if rng.range(0, 2) == 1 {
                        apply_horizontal_tunnel(map, prev_x, new_x, prev_y);
                        apply_vertical_tunnel(map, prev_y, new_y, new_x);
                    } else {
                        apply_vertical_tunnel(map, prev_y, new_y, prev_x);
                        apply_horizontal_tunnel(map, prev_x, new_x, new_y);
                    }
                }
                map.rooms.push(new_room);
            }
        }

        let stairs_position = map.rooms[map.rooms.len() - 1].center();
        let stairs_idx = map.xy_idx(stairs_position.0, stairs_position.1);
        map.tiles[stairs_idx] = TileType::DownStairs;
        let start_pos = map.rooms[0].center();
        Position { x: start_pos.0, y: start_pos.1}
    }
}
