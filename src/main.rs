use bevy::prelude::*;
use board::Position;
use coord::Coord;
use state::NextStateEvent;
use crate::state::{AppState, GameState};

mod board;
mod coord;
mod graphics;
mod input;
mod state;
mod actions;
use rand;

#[derive(Component)]
pub struct Player;

#[derive(Component)]
struct Mob;

#[derive(Component)]
pub struct Piece {
    pub kind: String,
}

#[derive(Component, Default)]
pub struct Actor(pub Option<Box<dyn actions::Action>>);

fn main() {
    App::new()
        .add_plugins((
            DefaultPlugins.set(
                //prevent linear filtering from blurring pixel art
                ImagePlugin::default_nearest(),
            ),
            MaleficerPlugin,
        ))
        .run();
}

#[derive(Component)]
struct GameCamera;

fn setup(mut commands: Commands) {
    let mut camera = Camera2dBundle::default();
    camera.transform.translation = Vec3::new(
        4. * graphics::TILE_SIZE, // TODO: why 4?
        4. * graphics::TILE_SIZE,
        camera.transform.translation.z,
    );
    commands.spawn((camera, GameCamera));
    info!("Enter to start");
}

fn spawn_player(
    mut commands: Commands,
    asset_server: Res<AssetServer>,
    mut texture_atlases: ResMut<Assets<TextureAtlas>>,
) {
    let texture_handle = asset_server.load("player.png");
    let texture_atlas =
        TextureAtlas::from_grid(texture_handle, Vec2::new(16.0, 16.0), 8, 9, None, None);
    let texture_atlas_handle = texture_atlases.add(texture_atlas);

    let _ssb = SpriteSheetBundle {
        texture_atlas: texture_atlas_handle,
        sprite: TextureAtlasSprite::new(8),
        transform: Transform::from_scale(Vec3::splat(2.0)),
        ..default()
    };
    commands.spawn((
        Player,
        Actor::default(),
        Piece {
            kind: "Player".to_string(),
        },
        board::Position {
            c: Coord::new(0, 0),
        },
    ));
}

fn spawn_mobs(mut commands: Commands) {
    commands.spawn((
        Mob,
        Actor::default(),
        Piece {
            kind: "Mob".to_string(),
        },
        board::Position {
            c: Coord::new(4, 4),
        },
    ));
    commands.spawn((
        Mob,
        Piece {
            kind: "Mob".to_string(),
        },
        board::Position {
            c: Coord::new(2, 4),
        },
    ));
}

fn mob_ai(mut mobs: Query<&mut Position, With<Mob>>,
    mut ev_state: EventWriter<NextStateEvent>,
) {
    for mut position in mobs.iter_mut() {
        if rand::random(){
            position.c += Coord::UP;
        }
        else {
            position.c += Coord::DOWN;
        }
    }
    ev_state.send(NextStateEvent);
}

fn enter_to_start(
    mut keys: ResMut<Input<KeyCode>>,
    mut next_state: ResMut<NextState<AppState>>,
) {
    // TODO: this eventually becomes a menu system
    if keys.just_pressed(KeyCode::Return) {
        next_state.set(AppState::InGame);
        dbg!("entering game");
        keys.reset(KeyCode::Return);
    }
}


pub struct MaleficerPlugin;

impl Plugin for MaleficerPlugin {
    fn build(&self, app: &mut App) {
        app.add_systems(Startup, setup)
            .add_systems(Update, enter_to_start.run_if(in_state(AppState::Menu)))
            .add_systems(Update, mob_ai.run_if(in_state(GameState::AITurn)))
            .add_plugins(board::BoardPlugin)
            .add_plugins(graphics::GraphicsPlugin)
            .add_plugins(input::InputPlugin)
            .add_plugins(state::StatePlugin)
            .add_plugins(state::ManagerPlugin)
            .add_plugins(actions::ActionsPlugin)
            .add_systems(OnEnter(AppState::InGame), (spawn_player, spawn_mobs));
    }
}
