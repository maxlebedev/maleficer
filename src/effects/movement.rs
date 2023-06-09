use specs::prelude::*;
use super::*;
use crate::{Position, Viewshed, Player};

pub fn apply_teleport(ecs: &mut World, destination: &EffectSpawner, tile_idx: i32) {
    let map = ecs.fetch::<Map>();
    let mut players = ecs.write_storage::<Player>();
    let mut positions = ecs.write_storage::<Position>();
    let mut viewsheds = ecs.write_storage::<Viewshed>();
    let (x,y) = map.idx_xy(tile_idx as usize);
    if let EffectType::TeleportTo{..} = &destination.effect_type {
        for (_player, pos, viewshed) in
            (&mut players, &mut positions, &mut viewsheds).join(){
                pos.x = x;
                pos.y = y;
                viewshed.dirty = true;
                // TODO: also recenter the camera
            }
        //TODO: apply teleport needs a whole movement system
        // TODO: allow for non-player things to tp too
    }
}
