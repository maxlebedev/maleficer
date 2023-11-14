use bevy::prelude::*;
use std::collections::HashMap;
use crate::coord::Coord;
use super::AppState;

#[derive(Component)]
pub struct Position {
    pub c: Coord
}

#[derive(Component)]
pub struct Tile;


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

pub struct BoardPlugin;

impl Plugin for BoardPlugin {
    fn build(&self, app: &mut App) {
        app.init_resource::<CurrentBoard>()
            .add_systems(OnEnter(AppState::Game), spawn_map);
    }
}

#[derive(Default, Resource)]
pub struct CurrentBoard {
    pub tiles: HashMap<Coord, Entity>
}
