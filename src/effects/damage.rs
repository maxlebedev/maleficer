use super::*;
use crate::{components::EntityStats, COLORS};
use specs::prelude::*;

pub fn inflict_damage(ecs: &mut World, damage: &EffectSpawner, target: Entity) {
    let mut entity_stats = ecs.write_storage::<EntityStats>();
    if let Some(pool) = entity_stats.get_mut(target) {
        if let EffectType::Damage { amount } = damage.effect_type {
            pool.deplete("hit_points", amount);
            add_effect(
                None,
                EffectType::Particle {
                    glyph: rltk::to_cp437('‼'),
                    fg: COLORS.orange,
                    bg: COLORS.black,
                    lifespan: 100.0,
                },
                Targets::Single { target },
            );
        }
    }
}

pub fn heal_damage(ecs: &mut World, damage: &EffectSpawner, target: Entity) {
    let mut entity_stats = ecs.write_storage::<EntityStats>();

    if let Some(pool) = entity_stats.get_mut(target) {
        if let EffectType::Healing { amount } = damage.effect_type {
            pool.restore("hit_points", amount);
            add_effect(
                None,
                EffectType::Particle {
                    glyph: rltk::to_cp437('♥'),
                    fg: COLORS.green,
                    bg: COLORS.black,
                    lifespan: 100.0,
                },
                Targets::Single { target },
            );
        }
    }
}

pub fn bloodstain(ecs: &mut World, tile_idx: i32) {
    let mut map = ecs.fetch_mut::<Map>();
    map.bloodstains.insert(tile_idx as usize);
}
