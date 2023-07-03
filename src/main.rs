use bevy::prelude::*;
use bevy_ascii_terminal::TerminalPlugin;
use bevy_ascii_terminal::{TerminalBundle, TiledCameraBundle};

mod config;
mod camera;
mod gui;
mod components;
mod events;
mod gamelog;
pub use components::*;

use rltk::RGB;

#[macro_use]
extern crate lazy_static;

#[derive(Debug, Default, Clone, Copy, Eq, PartialEq, Hash, States)]
pub enum RunState {
    #[default]
    AwaitingInput,
    PreRun,
    CharGen, // selection
    PlayerTurn,
    MonsterTurn,
    ShowInventory, // selection
    ShowTargeting, //range, item, radius 
    MainMenu, //game_started, menu_selection
    NextLevel,
}

#[derive(Component)]
pub struct GameTerminal;

pub const VIEWPORT_SIZE: [u32;2] = [80,40];
pub const UI_SIZE: [u32;2] = [VIEWPORT_SIZE[0],8];
// TODO: Map size should be separate
pub const GAME_SIZE: [u32;2] = [VIEWPORT_SIZE[0], VIEWPORT_SIZE[1] - UI_SIZE[1]];


/// converty bevy colors to rltk rgb
fn to_rgb(color : Color) -> RGB {
    let foo = color.as_rgba_f32();
    RGB::from_f32(foo[0], foo[1], foo[2])
}


fn setup(mut commands: Commands) {
    //commands.spawn().insert(gen.map);

    let term_bundle = TerminalBundle::new().with_size([GAME_SIZE[0], GAME_SIZE[1] + 2]);
    commands.spawn(term_bundle).insert(GameTerminal);

    let totalx = GAME_SIZE[0];
    let totaly = GAME_SIZE[1] + UI_SIZE[1];
    commands.spawn(TiledCameraBundle::new().with_tile_count([totalx, totaly]));
}

fn main() {
    App::new()
        .add_plugins(DefaultPlugins)
        .add_plugin(TerminalPlugin)
        .insert_resource(ClearColor(Color::BLACK))
        .add_startup_system(setup)
        .add_state::<RunState>()
        .run();
}
