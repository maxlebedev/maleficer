use specs::prelude::*;
use super::*;
use crate::components::ApplyTeleport;

pub fn apply_teleport(ecs: &mut World, destination: &EffectSpawner, target: Entity) {
    let player_entity = ecs.fetch::<Entity>();
    if let EffectType::TeleportTo{x, y} = &destination.effect_type {
        // TODO: the target is the thing being effected, so where are the destx/y?
        if target == *player_entity {
            let mut apply_teleport = ecs.write_storage::<ApplyTeleport>();
            apply_teleport.insert(target, ApplyTeleport{
                dest_x : *x,
                dest_y : *y,
            }).expect("Unable to insert");
        }
    }
}
