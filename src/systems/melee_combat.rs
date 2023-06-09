use crate::effects::{add_effect, EffectType, Targets};
use crate::{EntityStats, GameLog, Name, WantsToMelee};
use specs::prelude::*;

pub struct MeleeCombat {}

impl<'a> System<'a> for MeleeCombat {
    type SystemData = (
        Entities<'a>,
        WriteExpect<'a, GameLog>,
        WriteStorage<'a, WantsToMelee>,
        ReadStorage<'a, Name>,
        ReadStorage<'a, EntityStats>,
    );
    //TODO: what's the diff btw WriteStorage and WriteExpect

    fn run(&mut self, data: Self::SystemData) {
        let (
            entities,
            mut log,
            mut wants_melee,
            names,
            entity_stats,
        ) = data;

        for (entity, wants_melee, name, stats) in
            (&entities, &wants_melee, &names, &entity_stats).join()
        {
            if stats.get("hit_points").0 > 0 {
                let target_stats = entity_stats.get(wants_melee.target).unwrap();
                if target_stats.get("hit_points").0 > 0 {
                    let target_name = names.get(wants_melee.target).unwrap();

                    let damage = i32::max(0, stats.power - target_stats.defense);

                    if damage == 0 {
                        log.entries.push(format!(
                            "{} is unable to hurt {}",
                            &name.name, &target_name.name
                        ));
                    } else {
                        log.entries.push(format!(
                            "{} hits {}, for {} hp.",
                            &name.name, &target_name.name, damage
                        ));
                        add_effect(
                            Some(entity),
                            EffectType::Damage { amount: damage },
                            Targets::Single {
                                target: wants_melee.target,
                            },
                        );
                    }
                }
            }
        }

        wants_melee.clear();
    }
}
