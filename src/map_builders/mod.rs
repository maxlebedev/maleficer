use crate::Position;

use super::Map;
mod simple_map;
use simple_map::SimpleMapBuilder;
use specs::World;
pub mod common;

trait MapBuilder {
    fn build(new_depth: i32, width: i32, height: i32) -> (Map, Position);
    fn spawn(map: &Map, ecs: &mut World);

}
pub fn build_random_map(new_depth: i32, width: i32, height: i32) -> (Map, Position) {
    SimpleMapBuilder::build(new_depth, width, height)
}

pub fn spawn(map : &Map, ecs : &mut World) {
    SimpleMapBuilder::spawn(map, ecs);
}
