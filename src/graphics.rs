use bevy::prelude::*;
use super::{AppState, GameState};

use crate::board::{Position, Tile};

pub const TILE_SIZE: f32 = 32.;
pub const TILE_Z: f32 = 0.;
pub const PIECE_Z: f32 = 1.;

#[derive(Resource)]
pub struct GraphicsAssets {
    pub sprite_texture: Handle<TextureAtlas>
}

const ATLAS_PATH: &str = "ascii.png";

// TODO: not keeping an asset list like the tut does. Is this bad?
pub fn load_assets(
    mut commands: Commands,
    asset_server: Res<AssetServer>,
    mut texture_atlasses: ResMut<Assets<TextureAtlas>>,
) {
    let texture = asset_server.load(ATLAS_PATH);
    let atlas = TextureAtlas::from_grid(
        texture,
        Vec2::splat(10.),
        16,
        16,
        None,
        None
    );
    let handle = texture_atlasses.add(atlas);
    commands.insert_resource(
        GraphicsAssets { sprite_texture: handle }
    );
}

pub fn spawn_tile_renderer(
    mut commands: Commands,
    query: Query<(Entity, &Position), Added<Tile>>,
    assets: Res<GraphicsAssets>
) {
    for (entity, position) in query.iter() {
        let mut sprite = TextureAtlasSprite::new(177);
        sprite.custom_size = Some(Vec2::splat(TILE_SIZE));
        sprite.color = Color::LIME_GREEN;
        let v = get_world_position(position, TILE_Z);
        commands.entity(entity)
            .insert(
                SpriteSheetBundle {
                    sprite,
                    texture_atlas: assets.sprite_texture.clone(),
                    transform: Transform::from_translation(v),
                    ..Default::default()
                }
            );
    }
}

use super::Piece;

pub fn spawn_piece_renderer(
    mut commands: Commands,
    query: Query<(Entity, &Position, &Piece), Added<Piece>>,
    assets: Res<GraphicsAssets>
) {
    for (entity, position, piece) in query.iter() {
        dbg!(&piece.kind);
        let sprite_idx = match piece.kind.as_str() {
            "Player" => 1,
            _ => 63
        };
        let mut sprite = TextureAtlasSprite::new(sprite_idx);
        sprite.custom_size = Some(Vec2::splat(TILE_SIZE));
        sprite.color = Color::WHITE;
        let v = get_world_position(&position, PIECE_Z);
        commands.entity(entity)
            .insert(
                SpriteSheetBundle {
                    sprite,
                    texture_atlas: assets.sprite_texture.clone(),
                    transform: Transform::from_translation(v),
                    ..Default::default()
                }
            );
    }
}


fn get_world_position(
    position: &Position,
    z: f32
) -> Vec3 {
    Vec3::new(
        TILE_SIZE * position.c.x as f32,
        TILE_SIZE * position.c.y as f32,
        z
    )
}

const PIECE_SPEED: f32 = 10.;
const POSITION_TOLERANCE : f32 = 0.1;

pub fn update_piece_position(
    mut query: Query<(&Position, &mut Transform), With<Piece>>,
        time: Res<Time>,
) {
    for (position, mut transform) in query.iter_mut() {
        let target = get_world_position(&position, PIECE_Z);
        let d = (target - transform.translation).length();
        if d > POSITION_TOLERANCE {
            transform.translation = transform.translation.lerp(
                target,
                PIECE_SPEED * time.delta_seconds()
            );
        } else {
            transform.translation = target;
        }
    }
}

pub struct GraphicsPlugin;

impl Plugin for GraphicsPlugin {
    fn build(&self, app: &mut App) {
        app.add_systems(Startup, load_assets)
        .add_systems(Update, (spawn_tile_renderer, spawn_piece_renderer, update_piece_position).run_if(in_state(AppState::InGame)))
        .add_systems(Update, (update_piece_position).run_if(in_state(GameState::TurnResolution)))
        ;

    }
}
