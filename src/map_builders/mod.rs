use crate::Position;

use super::Map;
mod simple_map;
use simple_map::SimpleMapBuilder;
use specs::World;
pub mod common;

pub trait MapBuilder {
    fn build_map(&mut self, new_depth: i32, width: i32, height: i32) -> (Map, Position);
    fn spawn_entities(&mut self, map: &Map, ecs: &mut World);

}

pub fn random_builder() -> Box<dyn MapBuilder> {
    // Note that until we have a second map type, this isn't even slighlty random
    Box::new(SimpleMapBuilder::new())
}
