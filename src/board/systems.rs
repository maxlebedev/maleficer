use bevy::prelude::*;
use std::collections::HashMap;

use crate::coord::Coord;

use super::CurrentBoard;
use super::components::{Position, Tile};

pub fn spawn_map(
    mut commands: Commands,
    mut current: ResMut<CurrentBoard>
) {
    current.tiles = HashMap::new();
    for x in 0..8 {
        for y in 0..8 {
            let c = Coord::new(x, y);
            let tile = commands.spawn((
                    Position { c },
                    Tile
                ))
                .id();
            current.tiles.insert(c, tile);
        }
    }
}
