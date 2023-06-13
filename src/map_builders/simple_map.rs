use std::f32::INFINITY;

use crate::rect::Rect;
use crate::spawner;
use crate::Position;
use crate::TileType;

use super::common::*;
use super::Map;
use super::MapBuilder;
use rltk::Point;
use rltk::RandomNumberGenerator;
use specs::World;

pub struct SimpleMapBuilder {
    map: Map,
    starting_position: Position,
    depth: i32,
    rooms: Vec<Rect>,
}

impl MapBuilder for SimpleMapBuilder {
    fn build_map(&mut self) {
        self.rooms_and_corridors();
    }

    fn spawn_entities(&mut self, ecs: &mut World) {
        for room in self.rooms.iter().skip(1) {
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
    pub fn new(depth: i32, width: i32, height: i32) -> SimpleMapBuilder {
        SimpleMapBuilder {
            map: Map::new(depth, width, height),
            starting_position: Position { x: 0, y: 0 },
            depth,
            rooms: Vec::new(),
        }
    }

    /// Makes a new map using the algorithm from http://rogueliketutorials.com/tutorials/tcod/part-3/
    /// This gives a handful of random rooms and corridors joining them together.
    pub fn rooms_and_corridors(&mut self) {
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
            for other_room in self.rooms.iter() {
                if new_room.intersect(other_room) {
                    // TODO: I think this is broken, but I might perfer intersections
                    ok = false
                }
            }
            if ok {
                apply_room_to_map(&mut self.map, &new_room);
                self.rooms.push(new_room);
            }
        }

        for i in 0..self.rooms.len() - 1 {
            let (x, y) = self.rooms[i].center();
            let this_room = Point { x, y };
            let mut closest_room = Point { x: 0, y: 0 };
            let mut min_distance = INFINITY;
            for j in i + 1..self.rooms.len() {
                let (x, y) = self.rooms[j].center();
                let old_room = Point { x, y };
                let distance = rltk::DistanceAlg::Pythagoras.distance2d(this_room, old_room);
                if distance < min_distance {
                    min_distance = distance;
                    closest_room = old_room;
                }
            }
            if rng.range(0, 2) == 1 {
                apply_horizontal_tunnel(&mut self.map, closest_room.x, this_room.x, closest_room.y);
                apply_vertical_tunnel(&mut self.map, closest_room.y, this_room.y, this_room.x);
            } else {
                apply_vertical_tunnel(&mut self.map, closest_room.y, this_room.y, closest_room.x);
                apply_horizontal_tunnel(&mut self.map, closest_room.x, this_room.x, this_room.y);
            }
        }

        let stairs_position = self.rooms[self.rooms.len() - 1].center();
        let stairs_idx = self.map.xy_idx(stairs_position.0, stairs_position.1);
        self.map.tiles[stairs_idx] = TileType::DownStairs;
        let start_pos = self.rooms[0].center();
        self.starting_position = Position {
            x: start_pos.0,
            y: start_pos.1,
        }
    }
}
