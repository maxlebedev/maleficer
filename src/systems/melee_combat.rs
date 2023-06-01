use crate::systems::particle::ParticleBuilder;
use crate::{EntityStats, GameLog, Name, Position, SufferDamage, WantsToMelee, COLORS};
use specs::prelude::*;
// use rltk::console;

pub struct MeleeCombat {}

impl<'a> System<'a> for MeleeCombat {
    type SystemData = (
        Entities<'a>,
        WriteExpect<'a, GameLog>,
        WriteStorage<'a, WantsToMelee>,
        ReadStorage<'a, Name>,
        ReadStorage<'a, EntityStats>,
        WriteStorage<'a, SufferDamage>,
        WriteExpect<'a, ParticleBuilder>,
        ReadStorage<'a, Position>,
    );
    //TODO: what's the diff btw WriteStorage and WriteExpect

    fn run(&mut self, data: Self::SystemData) {
        let (
            entities,
            mut log,
            mut wants_melee,
            names,
            entity_stats,
            mut inflict_damage,
            mut particle_builder,
            positions,
        ) = data;

        for (_entity, wants_melee, name, stats) in
            (&entities, &wants_melee, &names, &entity_stats).join()
        {
            if stats.get("hit_points").0 > 0 {
                let target_stats = entity_stats.get(wants_melee.target).unwrap();
                if target_stats.get("hit_points").0 > 0 {
                    let target_name = names.get(wants_melee.target).unwrap();

                    let pos = positions.get(wants_melee.target);
                    if let Some(pos) = pos {
                        particle_builder.request(
                            pos.x,
                            pos.y,
                            COLORS.orange,
                            COLORS.black,
                            rltk::to_cp437('‼'),
                            100.0,
                        );
                    }
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
                        SufferDamage::new_damage(&mut inflict_damage, wants_melee.target, damage);
                    }
                }
            }
        }

        wants_melee.clear();
    }
}
