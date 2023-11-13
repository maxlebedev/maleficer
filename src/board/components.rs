use bevy::prelude::*;
use crate::coord::Coord;

#[derive(Component)]
pub struct Position {
    pub c: Coord
}

#[derive(Component)]
pub struct Tile;

