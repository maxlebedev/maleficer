use specs::prelude::*;

use crate::{
    Consumable, GameLog, InflictsDamage, ProvidesHealing, SpawnParticleBurst, SpawnParticleLine,
    TeleportTo, COLORS, ProvidesMana, CostsMana,
};

use super::*;

pub fn item_trigger(creator: Option<Entity>, item: Entity, targets: &Targets, ecs: &mut World) {
    // Use the item via the generic system
    let did_something = event_trigger(creator, item, targets, ecs);

    // If it was a consumable, then it gets deleted
    if did_something && ecs.read_storage::<Consumable>().get(item).is_some() {
        ecs.entities().delete(item).expect("Delete Failed");
    }
}

fn spawn_line_particles(ecs: &World, start: i32, end: i32, part: &SpawnParticleLine) {
    // TODO: this is wildly inaccurate
    let map = ecs.fetch::<Map>();
    let start_pt = rltk::Point::new(start % map.width, end / map.width);
    let end_pt = rltk::Point::new(end % map.width, end / map.width);
    let line = rltk::line2d(rltk::LineAlg::Bresenham, start_pt, end_pt);
    for pt in line.iter() {
        add_effect(
            None,
            EffectType::Particle {
                glyph: part.glyph,
                fg: part.color,
                bg: rltk::RGB::named(rltk::BLACK),
                lifespan: part.lifetime_ms,
            },
            Targets::Tile {
                tile_idx: map.xy_idx(pt.x, pt.y) as i32,
            },
        );
    }
}

fn event_trigger(
    creator: Option<Entity>,
    entity: Entity,
    targets: &Targets,
    ecs: &mut World,
) -> bool {
    let mut did_something = false;
    // let mut _gamelog = ecs.fetch_mut::<GameLog>();
    // Simple particle spawn
    if let Some(part) = ecs.read_storage::<SpawnParticleBurst>().get(entity) {
        add_effect(
            creator,
            EffectType::Particle {
                glyph: part.glyph,
                fg: part.color,
                bg: COLORS.black,
                lifespan: part.lifetime_ms,
            },
            targets.clone(),
        );
    }
    // Line particle spawn
    if let Some(part) = ecs.read_storage::<SpawnParticleLine>().get(entity) {
        if let Some(start_pos) = targeting::find_item_position(ecs, entity) {
            match targets {
                Targets::Tile { tile_idx } => spawn_line_particles(ecs, start_pos, *tile_idx, part),
                Targets::Tiles { tiles } => tiles
                    .iter()
                    .for_each(|tile_idx| spawn_line_particles(ecs, start_pos, *tile_idx, part)),
                Targets::Single { target } => {
                    if let Some(end_pos) = entity_position(ecs, *target) {
                        spawn_line_particles(ecs, start_pos, end_pos, part);
                    }
                }
                Targets::TargetList { targets } => {
                    targets.iter().for_each(|target| {
                        if let Some(end_pos) = entity_position(ecs, *target) {
                            spawn_line_particles(ecs, start_pos, end_pos, part);
                        }
                    });
                }
            }
        }
    }

    // we write a lambda here to avoid borrowing ecs as mutable and immutable in the smae scope
    let get_player_target = |ecs: &mut World| Targets::Single{target:*ecs.fetch::<Entity>()};
    let player_target = get_player_target(ecs);
    // Healing
    if let Some(heal) = ecs.read_storage::<ProvidesHealing>().get(entity) {
        add_effect(
            creator,
            EffectType::Healing {
                amount: heal.heal_amount,
            },
            player_target.clone(),
        );
        did_something = true;
    }

    // Gain Mana
    if let Some(mana) = ecs.read_storage::<ProvidesMana>().get(entity) {
        add_effect(
            creator,
            EffectType::GainMana {
                amount: mana.mana_amount,
            },
            player_target.clone(),
        );
        did_something = true;
    }
    // Lose Mana
    if let Some(mana) = ecs.read_storage::<CostsMana>().get(entity) {
        add_effect(
            creator,
            EffectType::LoseMana {
                amount: mana.mana_amount,
            },
            player_target.clone(),
        );
        did_something = true;
    }
    // Damage
    if let Some(damage) = ecs.read_storage::<InflictsDamage>().get(entity) {
        add_effect(
            creator,
            EffectType::Damage {
                amount: damage.damage,
            },
            targets.clone(),
        );
        did_something = true;
    }

    // Teleport
    if let Some(teleport) = ecs.read_storage::<TeleportTo>().get(entity) {
        add_effect(
            creator,
            EffectType::TeleportTo {
                x: teleport.x,
                y: teleport.y,
            },
            targets.clone(),
        );
        did_something = true;
    }
    did_something
}
