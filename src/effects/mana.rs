use super::*;
use crate::{components::EntityStats, gamelog};
use specs::prelude::*;

pub fn lose_mana(ecs: &mut World, lose_mana: &EffectSpawner, target: Entity) {
    let mut entity_stats = ecs.write_storage::<EntityStats>();
    if let Some(pool) = entity_stats.get_mut(target) {
        if let EffectType::LoseMana { amount } = lose_mana.effect_type {
            let current_mana = pool.get("mana").0;
            if  current_mana >= amount {
                pool.deplete("mana", amount);
            }
            else{
                // we don't stop you from casting spells without mana, you just lose
                // 2xMana in HP
                let mut gamelog = ecs.fetch_mut::<gamelog::GameLog>();
                gamelog.entries.push("Insufficient mana. Paying in blood".to_string());

                pool.set_current("mana", 0);
                let damage = 2 * (amount - current_mana);
                add_effect(
                    None,
                    EffectType::Damage {amount: damage},
                    Targets::Single { target },
                );
            }
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
