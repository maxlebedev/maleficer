use bevy::prelude::*;
use std::collections::HashMap;

pub mod components;
mod systems;

use crate::coord::Coord;

use self::systems::spawn_map;

pub struct BoardPlugin;

impl Plugin for BoardPlugin {
    fn build(&self, app: &mut App) {
        app.init_resource::<CurrentBoard>()
        .add_systems(Startup, spawn_map);
        // .add_system(systems::spawn_map.in_schedule(OnEnter(MainState::Game)));
    }
}

#[derive(Default, Resource)]
pub struct CurrentBoard {
    pub tiles: HashMap<Coord, Entity>
}
