use crate::Position;

use super::Map;
mod simple_map;
use simple_map::SimpleMapBuilder;
use specs::World;
pub mod common;

pub trait MapBuilder {
    fn build_map(&mut self);
    fn spawn_entities(&mut self, ecs: &mut World);
    fn get_map(&self) -> Map;
    fn get_starting_position(&self) -> Position;
}

pub fn random_builder(depth:i32,width: i32, height: i32) -> Box<dyn MapBuilder> {
    // Note that until we have a second map type, this isn't even slighlty random
    Box::new(SimpleMapBuilder::new(depth,width, height))
}
