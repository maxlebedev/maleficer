use bevy::prelude::*;

use crate::board::components::{Position, Tile};

pub const TILE_SIZE: f32 = 32.;

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
        sprite.color = Color::OLIVE;
        let v = Vec3::new(
            TILE_SIZE * position.c.x as f32,
            TILE_SIZE * position.c.y as f32,
            0.
        );
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

pub struct GraphicsPlugin;

impl Plugin for GraphicsPlugin {
    fn build(&self, app: &mut App) {
        app.add_systems(Startup, load_assets)
            //post startup because it depends on load_assets
        .add_systems(PostStartup, spawn_tile_renderer);

    }
}
