use crate::{
    camera, gamelog::GameLog, map::Map, Antagonistic, AreaOfEffect, Consumable, Cursor,
    EntityStats, InBackpack, InflictsDamage, Name, Position, ProvidesHealing, Ranged, RunState,
    WantsToDropItem, WantsToPickupItem, WantsToUseItem, COLORS, effects::*,
};
use rltk::Point;
use specs::prelude::*;

use super::particle::ParticleBuilder;

pub struct ItemCollection {}

impl<'a> System<'a> for ItemCollection {
    #[allow(clippy::type_complexity)]
    type SystemData = (
        ReadExpect<'a, Entity>,
        WriteExpect<'a, GameLog>,
        WriteStorage<'a, WantsToPickupItem>,
        WriteStorage<'a, Position>,
        ReadStorage<'a, Name>,
        WriteStorage<'a, InBackpack>,
    );

    fn run(&mut self, data: Self::SystemData) {
        let (player_entity, mut gamelog, mut wants_pickup, mut positions, names, mut backpack) =
            data;

        for pickup in wants_pickup.join() {
            positions.remove(pickup.item);
            backpack
                .insert(
                    pickup.item,
                    InBackpack {
                        owner: pickup.collected_by,
                    },
                )
                .expect("Unable to insert backpack entry");

            if pickup.collected_by == *player_entity {
                gamelog.entries.push(format!(
                    "You pick up the {}.",
                    names.get(pickup.item).unwrap().name
                ));
            }
        }

        wants_pickup.clear();
    }
}

pub struct ItemUse {}

impl<'a> System<'a> for ItemUse {
    #[allow(clippy::type_complexity)]
    type SystemData = (
        ReadExpect<'a, Entity>,
        WriteExpect<'a, GameLog>,
        Entities<'a>,
        WriteStorage<'a, WantsToUseItem>,
        ReadStorage<'a, Name>,
        ReadStorage<'a, Consumable>,
        ReadStorage<'a, ProvidesHealing>,
        ReadStorage<'a, InflictsDamage>,
        ReadExpect<'a, Map>,
        WriteStorage<'a, EntityStats>,
        ReadStorage<'a, AreaOfEffect>,
        WriteExpect<'a, ParticleBuilder>,
        ReadStorage<'a, Position>,
        ReadStorage<'a, Antagonistic>,
    );

    fn run(&mut self, data: Self::SystemData) {
        let (
            player_entity,
            mut gamelog,
            entities,
            mut wants_use,
            names,
            consumables,
            healing,
            inflict_damage,
            map,
            mut combat_stats,
            aoe,
            mut particle_builder,
            positions,
            antagonists,
        ) = data;

        for (entity, useitem) in (&entities, &wants_use).join() {
            let mut targets: Vec<Entity> = Vec::new();
            match useitem.target {
                None => {
                    targets.push(*player_entity);
                }
                Some(target) => {
                    let area_effect = aoe.get(useitem.item);
                    match area_effect {
                        None => {
                            // Single target in tile
                            let idx = map.xy_idx(target.x, target.y);
                            for mob in map.tile_content[idx].iter() {
                                targets.push(*mob);
                            }
                        }
                        Some(area_effect) => {
                            // AoE
                            let mut blast_tiles =
                                rltk::field_of_view(target, area_effect.radius, &*map);
                            blast_tiles.retain(|p| {
                                p.x > 0 && p.x < map.width - 1 && p.y > 0 && p.y < map.height - 1
                            });
                            for tile_idx in blast_tiles.iter() {
                                let idx = map.xy_idx(tile_idx.x, tile_idx.y);
                                for mob in map.tile_content[idx].iter() {
                                    targets.push(*mob);
                                }
                                particle_builder.request(
                                    tile_idx.x,
                                    tile_idx.y,
                                    COLORS.orange,
                                    COLORS.black,
                                    rltk::to_cp437('░'),
                                    200.0,
                                );
                            }
                        }
                    }
                }
            }

            let mut used_item = true;
            let item_heals = healing.get(useitem.item);

            match item_heals {
                None => {}
                Some(healer) => {
                    for potential_target in targets.iter() {
                        let mut target = potential_target;
                        let selected_antagonist = antagonists.get(*target);
                        if let Some(_target) = selected_antagonist {
                            target = &player_entity;
                        }
                        let stats = combat_stats.get_mut(*target).unwrap();
                        let (curr_hp, max_hp) = stats.get("hit_points");
                        let new_hp = i32::min(max_hp, curr_hp + healer.heal_amount);
                        stats.set_current("hit_points", new_hp);
                        if entity == *player_entity {
                            gamelog.entries.push(format!(
                                "The {} heals you for {} hp.",
                                names.get(useitem.item).unwrap().name,
                                healer.heal_amount
                            ));
                        }
                        let pos = positions.get(*target);
                        if let Some(pos) = pos {
                            particle_builder.request(
                                pos.x,
                                pos.y,
                                COLORS.green,
                                COLORS.black,
                                rltk::to_cp437('♥'),
                                200.0,
                            );
                        }
                    }
                }
            }
            // If it inflicts damage, apply it to the target cell
            let item_damages = inflict_damage.get(useitem.item);
            match item_damages {
                None => {}
                Some(damage) => {
                    used_item = false;
                    for mob in targets.iter() {
                        add_effect(
                            Some(*player_entity),
                            EffectType::Damage {
                                amount: damage.damage,
                            },
                            Targets::Single { target: *mob },
                        );
                        if entity == *player_entity {
                            let mob_name = names.get(*mob).unwrap();
                            let item_name = names.get(useitem.item).unwrap();
                            gamelog.entries.push(format!(
                                "You use {} on {}, inflicting {} damage.",
                                item_name.name, mob_name.name, damage.damage
                            ));

                            let pos = positions.get(*mob);
                            if let Some(pos) = pos {
                                particle_builder.request(
                                    pos.x,
                                    pos.y,
                                    COLORS.red,
                                    COLORS.black,
                                    rltk::to_cp437('‼'),
                                    200.0,
                                );
                            }
                        }
                        used_item = true;
                    }
                }
            }
            // If its a consumable, we delete it on use
            if used_item {
                let consumable = consumables.get(useitem.item);
                match consumable {
                    None => {}
                    Some(_) => {
                        entities.delete(useitem.item).expect("Delete failed");
                    }
                }
            }
        }

        wants_use.clear();
    }
}

pub struct ItemDrop {}

impl<'a> System<'a> for ItemDrop {
    #[allow(clippy::type_complexity)]
    type SystemData = (
        ReadExpect<'a, Entity>,
        WriteExpect<'a, GameLog>,
        Entities<'a>,
        WriteStorage<'a, WantsToDropItem>,
        ReadStorage<'a, Name>,
        WriteStorage<'a, Position>,
        WriteStorage<'a, InBackpack>,
    );

    fn run(&mut self, data: Self::SystemData) {
        let (
            player_entity,
            mut gamelog,
            entities,
            mut wants_drop,
            names,
            mut positions,
            mut backpack,
        ) = data;

        for (entity, to_drop) in (&entities, &wants_drop).join() {
            let mut dropper_pos: Position = Position { x: 0, y: 0 };
            {
                let dropped_pos = positions.get(entity).unwrap();
                dropper_pos.x = dropped_pos.x;
                dropper_pos.y = dropped_pos.y;
            }
            positions
                .insert(
                    to_drop.item,
                    Position {
                        x: dropper_pos.x,
                        y: dropper_pos.y,
                    },
                )
                .expect("Unable to insert position");
            backpack.remove(to_drop.item);

            if entity == *player_entity {
                gamelog.entries.push(format!(
                    "You drop the {}.",
                    names.get(to_drop.item).unwrap().name
                ));
            }
        }

        wants_drop.clear();
    }
}

pub fn use_item(ecs: &mut World, item: Entity) -> RunState {
    let is_aoe = ecs.read_storage::<AreaOfEffect>();
    let radius = match is_aoe.get(item) {
        Some(is_item_aoe) => is_item_aoe.radius,
        None => 0,
    };
    if let Some(ranged) = ecs.read_storage::<Ranged>().get(item) {
        //reset cursor position
        let player_pos = ecs.fetch::<Point>();
        let mut cursor = ecs.fetch_mut::<Cursor>();
        cursor.point = camera::tile_to_screen(ecs, *player_pos);
        return RunState::ShowTargeting {
            range: ranged.range,
            item,
            radius,
        };
    }
    let mut intent = ecs.write_storage::<WantsToUseItem>();
    intent
        .insert(
            *ecs.fetch::<Entity>(),
            WantsToUseItem { item, target: None },
        )
        .expect("Unable to insert intent");
    RunState::PlayerTurn
}
