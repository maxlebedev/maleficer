use super::*;
use crate::components::EntityStats;
use specs::prelude::*;

pub fn lose_mana(ecs: &mut World, lose_mana: &EffectSpawner, target: Entity) {
    let mut entity_stats = ecs.write_storage::<EntityStats>();
    if let Some(pool) = entity_stats.get_mut(target) {
        dbg!("losing mana");
        if let EffectType::LoseMana { amount } = lose_mana.effect_type {
            pool.deplete("mana", amount);
        }
    }
}

pub fn gain_mana(ecs: &mut World, gain_mana: &EffectSpawner, target: Entity) {
    let mut entity_stats = ecs.write_storage::<EntityStats>();
    if let Some(pool) = entity_stats.get_mut(target) {
        if let EffectType::GainMana { amount } = gain_mana.effect_type {
            pool.restore("mana", amount);
        }
    }
}
