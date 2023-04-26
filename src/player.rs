use crate::gui;

use super::gamelog::GameLog;
use rltk::{Point, Rltk};
use specs::prelude::*;

use super::{components, config, map, RunState, State};
pub use components::*;
use num;

fn _make_character() {
    // Here goes a function that initializes all of the rpgish character stuff
}

fn try_move_player(delta_x: i32, delta_y: i32, ecs: &mut World) {
    let mut positions = ecs.write_storage::<Position>();
    let mut players = ecs.write_storage::<Player>();
    let mut viewsheds = ecs.write_storage::<Viewshed>();

    let combat_stats = ecs.read_storage::<CombatStats>();
    let map = ecs.fetch::<map::Map>();

    let entities = ecs.entities();
    let mut wants_to_melee = ecs.write_storage::<WantsToMelee>();

    for (entity, _player, pos, viewshed) in
        (&entities, &mut players, &mut positions, &mut viewsheds).join()
    {
        if pos.x + delta_x < 1
            || pos.x + delta_x > map.width - 1
            || pos.y + delta_y < 1
            || pos.y + delta_y > map.height - 1
        {
            return;
        }

        let destination_idx = map.xy_idx(pos.x + delta_x, pos.y + delta_y);
        for potential_target in map.tile_content[destination_idx].iter() {
            let target = combat_stats.get(*potential_target);
            if let Some(_target) = target {
                wants_to_melee
                    .insert(
                        entity,
                        WantsToMelee {
                            target: *potential_target,
                        },
                    )
                    .expect("Add target failed");
                return;
            }
        }
        if !map.blocked[destination_idx] {
            pos.x = num::clamp(pos.x + delta_x, 0, map.width - 1);
            pos.y = num::clamp(pos.y + delta_y, 0, map.height - 1);

            let mut ppos = ecs.write_resource::<Point>();
            ppos.x = pos.x;
            ppos.y = pos.y;
            viewshed.dirty = true;
        }
    }
}

fn get_item(ecs: &mut World) {
    let player_pos = ecs.fetch::<Point>();
    let player_entity = ecs.fetch::<Entity>();
    let entities = ecs.entities();
    let items = ecs.read_storage::<Item>();
    let positions = ecs.read_storage::<Position>();
    let mut gamelog = ecs.fetch_mut::<GameLog>();

    let mut target_item: Option<Entity> = None;
    for (item_entity, _item, position) in (&entities, &items, &positions).join() {
        if position.x == player_pos.x && position.y == player_pos.y {
            target_item = Some(item_entity);
        }
    }

    match target_item {
        None => gamelog
            .entries
            .push("There is nothing here to pick up.".to_string()),
        Some(item) => {
            let mut pickup = ecs.write_storage::<WantsToPickupItem>();
            pickup
                .insert(
                    *player_entity,
                    WantsToPickupItem {
                        collected_by: *player_entity,
                        item,
                    },
                )
                .expect("Unable to insert want to pickup");
        }
    }
}

pub fn player_input(gs: &mut State, ctx: &mut Rltk) -> RunState {
    let left = config::cfg_to_kc(&config::CONFIG.left);
    let down = config::cfg_to_kc(&config::CONFIG.down);
    let up = config::cfg_to_kc(&config::CONFIG.up);
    let right = config::cfg_to_kc(&config::CONFIG.right);

    let pick_up = config::cfg_to_kc(&config::CONFIG.pick_up);
    let inventory = config::cfg_to_kc(&config::CONFIG.inventory);
    let exit = config::cfg_to_kc(&config::CONFIG.exit);
    let wait = config::cfg_to_kc(&config::CONFIG.wait);

    match ctx.key {
        None => return RunState::AwaitingInput, // Nothing happened
        Some(key) => match key {
            // TODO: I still don't understand why I have to do do `_ if key ==`
            _ if key == left => try_move_player(-1, 0, &mut gs.ecs),
            _ if key == down => try_move_player(0, 1, &mut gs.ecs),
            _ if key == up => try_move_player(0, -1, &mut gs.ecs),
            _ if key == right => try_move_player(1, 0, &mut gs.ecs),

            _ if key == pick_up => get_item(&mut gs.ecs),
            _ if key == inventory => return RunState::ShowInventory { selection: 0 },

            _ if key == exit => {
                return RunState::MainMenu {
                    menu_selection: gui::MainMenuSelection::NewGame,
                }
            }

            _ if key == wait => return RunState::PlayerTurn,

            _ => return RunState::AwaitingInput,
        },
    }
    RunState::PlayerTurn
}
