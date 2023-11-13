use bevy::prelude::*;

mod states;
mod board;
mod coord;
mod graphics;

#[derive(Component)]
struct Player;


fn main() {
    App::new()
        .add_plugins(
            (DefaultPlugins.set(
                //prevent linear filtering from blurring pixel art
                ImagePlugin::default_nearest(),
            ),
                MaleficerPlugin)
        )
        .run();
}

fn setup(mut commands: Commands, asset_server: Res<AssetServer>, mut texture_atlases: ResMut<Assets<TextureAtlas>>,) {
    commands.spawn(Camera2dBundle::default());

    let texture_handle = asset_server.load("player.png");
    let texture_atlas = TextureAtlas::from_grid(texture_handle, Vec2::new(16.0, 16.0), 8, 9, None, None);
    let texture_atlas_handle = texture_atlases.add(texture_atlas);

    /*
    commands.spawn(SpriteBundle {
        texture: asset_server.load("viper_map_tierlist.png"),
        ..default()
    });
    */

    let ssb = SpriteSheetBundle {
            texture_atlas: texture_atlas_handle,
            sprite: TextureAtlasSprite::new(8),
            transform: Transform::from_scale(Vec3::splat(2.0)),
        //  transform: Transform::from_translation(Vec3::ZERO);
            ..default()
        };
    commands.spawn((Player, ssb));
}

fn player_movement(mut player: Query<(&mut Player, &mut Transform)>){
    // TODO: this should recieve directional controls
    // TODO: the sprite thing has a postion that is different from our coords
    for (_, mut transform) in &mut player{
        transform.translation.y += 10.0;
    }

}

pub struct MaleficerPlugin;

impl Plugin for MaleficerPlugin{
    fn build(&self, app: &mut App) {
        app.add_systems(Startup, setup)
        .add_plugins(board::BoardPlugin)
        .add_plugins(graphics::GraphicsPlugin)
        ;
    }
}
