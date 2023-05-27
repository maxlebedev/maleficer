use crate::Position;
use crate::TileType;
use crate::rect::Rect;
use crate::spawner;

use super::MapBuilder;
use super::Map;
use super::common::*;
use rltk::RandomNumberGenerator;
use specs::World;


pub struct SimpleMapBuilder {
    map: Map,
    starting_position: Position,
    depth: i32
}

impl MapBuilder for SimpleMapBuilder {


    fn build_map(&mut self){
        self.rooms_and_corridors();
    }

    fn spawn_entities(&mut self, ecs : &mut World) {
        for room in self.map.rooms.iter().skip(1) {
            spawner::spawn_room(ecs, room, self.depth);
        }
    }

    fn get_map(&self) -> Map {
        self.map.clone()
    }

    fn get_starting_position(&self) -> Position {
        self.starting_position.clone()
    }

}

impl SimpleMapBuilder {

    pub fn new(depth:i32,width: i32, height: i32 ) -> SimpleMapBuilder {
        SimpleMapBuilder{
            map : Map::new(depth, width, height),
            starting_position : Position{ x: 0, y : 0 },
            depth
        }
    }

    /// Makes a new map using the algorithm from http://rogueliketutorials.com/tutorials/tcod/part-3/
    /// This gives a handful of random rooms and corridors joining them together.
    pub fn rooms_and_corridors(&mut self){
        const MAX_ROOMS: i32 = 30;
        const MIN_SIZE: i32 = 6;
        const MAX_SIZE: i32 = 10;

        let mut rng = RandomNumberGenerator::new();

        for _ in 0..MAX_ROOMS {
            let w = rng.range(MIN_SIZE, MAX_SIZE);
            let h = rng.range(MIN_SIZE, MAX_SIZE);
            let x = rng.range(1, self.map.width - w - 1);
            let y = rng.range(1, self.map.height - h - 1);
            let new_room = Rect::new(x, y, w, h);
            let mut ok = true;
            for other_room in self.map.rooms.iter() {
                if new_room.intersect(other_room) {
                    // TODO: I think this is broken, but I might perfer intersections
                    ok = false
                }
            }
            if ok {
                apply_room_to_map(&mut self.map, &new_room);
                if !self.map.rooms.is_empty() {
                    let (new_x, new_y) = new_room.center();
                    let (prev_x, prev_y) = self.map.rooms[self.map.rooms.len() - 1].center();
                    // prev is the most recent one, not the closest one
                    if rng.range(0, 2) == 1 {
                        apply_horizontal_tunnel(&mut self.map, prev_x, new_x, prev_y);
                        apply_vertical_tunnel(&mut self.map, prev_y, new_y, new_x);
                    } else {
                        apply_vertical_tunnel(&mut self.map, prev_y, new_y, prev_x);
                        apply_horizontal_tunnel(&mut self.map, prev_x, new_x, new_y);
                    }
                }
                self.map.rooms.push(new_room);
            }
        }

        let stairs_position = self.map.rooms[self.map.rooms.len() - 1].center();
        let stairs_idx = self.map.xy_idx(stairs_position.0, stairs_position.1);
        self.map.tiles[stairs_idx] = TileType::DownStairs;
        let start_pos = self.map.rooms[0].center();
        self.starting_position = Position { x: start_pos.0, y: start_pos.1}
    }
}
