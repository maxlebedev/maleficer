use bevy::prelude::*;
use std::collections::HashMap;
use crate::coord::Coord;
use self::systems::spawn_map;
use super::AppState;

pub mod components;
mod systems;


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
