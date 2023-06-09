use super::save_load;
use crate::{EntityStats, GameLog, Name, Player, effects::*};
use rltk::console;
use specs::prelude::*;

pub fn delete_the_dead(ecs: &mut World) {
    let mut dead: Vec<Entity> = Vec::new();
    // Using a scope to make the borrow checker happy
    {
        let combat_stats = ecs.read_storage::<EntityStats>();
        let players = ecs.read_storage::<Player>();
        let names = ecs.read_storage::<Name>();
        let entities = ecs.entities();
        let mut log = ecs.write_resource::<GameLog>();
        for (entity, stats) in (&entities, &combat_stats).join() {
            if stats.get("hit_points").0 < 1 {
                let player = players.get(entity);
                match player {
                    None => {
                        let victim_name = names.get(entity);
                        if let Some(victim_name) = victim_name {
                            log.entries
                                .push(format!("{} is no more", &victim_name.name));
                        }
                        dead.push(entity);
                        if let Some(tile_idx) = entity_position(ecs, entity) {
                            add_effect(None, EffectType::Bloodstain, Targets::Tile { tile_idx });
                        }
                    }
                    Some(_) => {
                        console::log("You are dead");
                        save_load::delete_save();
                        ::std::process::exit(0);
                    }
                }
            }
        }
    }
    for victim in dead {
        ecs.delete_entity(victim).expect("Unable to delete");
    }
}
