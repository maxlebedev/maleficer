use crate::{
    camera, effects::*, gamelog::GameLog, map::Map, AreaOfEffect, Cursor, InBackpack, Name,
    Position, Ranged, RunState, WantsToPickupItem, WantsToUseItem,
};
use rltk::Point;
use specs::prelude::*;

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
        Entities<'a>,
        WriteStorage<'a, WantsToUseItem>,
        ReadExpect<'a, Map>,
        ReadStorage<'a, AreaOfEffect>,
    );

    fn run(&mut self, data: Self::SystemData) {
        let (player_entity, entities, mut wants_use, map, aoe) = data;

        for (entity, useitem) in (&entities, &wants_use).join() {
            add_effect(
                Some(entity),
                EffectType::ItemUse { item: useitem.item },
                match useitem.target {
                    None => Targets::Single {
                        target: *player_entity,
                    },
                    Some(target) => {
                        if let Some(aoe) = aoe.get(useitem.item) {
                            Targets::Tiles {
                                tiles: aoe_tiles(&*map, target, aoe.radius),
                            }
                        } else {
                            Targets::Tile {
                                tile_idx: map.xy_idx(target.x, target.y) as i32,
                            }
                        }
                    }
                },
            );
        }
        wants_use.clear();
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
