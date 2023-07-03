use bevy::prelude::Resource;

#[derive(Resource, Default)]
pub struct GameLog {
    pub entries: Vec<String>,
}
