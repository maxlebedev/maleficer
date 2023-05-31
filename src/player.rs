use crate::{config::INPUT, gui};

use super::gamelog::GameLog;
use rltk::{Point, Rltk, VirtualKeyCode};
use specs::prelude::*;

use super::{components, config, map, systems, RunState, State};
pub use components::*;

pub fn make_character(ecs: &mut World) {
    // Here goes a function that initializes all of the rpgish character stuff
    // for now we just add a spell to the hotbar

    // TODO: look at the selection from prev menu and make diff spell
    systems::spell::fireball_spell(ecs, config::CONFIG.hk1.clone());
}

pub fn is_turn_blocked(x: i32, y: i32, ecs: &mut World) -> bool {
    let player_pos = ecs.fetch::<Point>();
    let map = ecs.fetch::<map::Map>();
    let dest_idx = map.xy_idx(player_pos.x + x, player_pos.y + y);

    if map.blocked[dest_idx] {
        return false;
    }
    return true;
}

fn try_move_player(delta_x: i32, delta_y: i32, ecs: &mut World) {
    let mut positions = ecs.write_storage::<Position>();
    let mut players = ecs.write_storage::<Player>();
    let mut viewsheds = ecs.write_storage::<Viewshed>();

    let antagonists = ecs.read_storage::<Antagonistic>();
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
            let target = antagonists.get(*potential_target);
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
            pos.x = i32::clamp(pos.x + delta_x, 0, map.width - 1);
            pos.y = i32::clamp(pos.y + delta_y, 0, map.height - 1);

            let mut ppos = ecs.write_resource::<Point>();
            ppos.x = pos.x;
            ppos.y = pos.y;
            viewshed.dirty = true;
        }
    }
}

fn _cast_spell(ecs: &mut World) {
    let player_entity = ecs.fetch::<Entity>();
    let cursor = ecs.fetch::<Cursor>();
    let mut castables = ecs.write_storage::<WantsToCastSpell>();
    // having some trouble with ecs here. spell isn't passed in here, we join it based on
    // keypress???

    // return RunState::ShowTargeting { range: (), item: () },

    //gui::ranged_target(ecs, ctx: &mut Rltk, range: i32);
    // -> SelectResult

    // Flow: press C, 1
    // move cursor, hit enter
    // spell takes effect
    //
    // Do we have a
    castables
        .insert(
            *player_entity,
            WantsToCastSpell {
                source: *player_entity,
                target: Some(cursor.point),
            },
        )
        .expect("Unable to insert want to cast");
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

fn use_hotkey(_ecs: &mut World, key: VirtualKeyCode) {
    // TODO: some kind of key:item entity lookup
    dbg!(key);
}

// TODO: protect from overflow on char/item select window

pub fn player_input(gs: &mut State, ctx: &mut Rltk) -> RunState {
    let hotkeys = vec![INPUT.hk1, INPUT.hk2, INPUT.hk3, INPUT.hk4];
    match ctx.key {
        None => return RunState::AwaitingInput, // Nothing happened
        Some(key) => match key {
            // TODO: I still don't understand why I have to do do `_ if key ==`
            _ if key == INPUT.left && is_turn_blocked(-1, 0, &mut gs.ecs) == true => {
                try_move_player(-1, 0, &mut gs.ecs)
            }
            _ if key == INPUT.down && is_turn_blocked(0, 1, &mut gs.ecs) == true => {
                try_move_player(0, 1, &mut gs.ecs)
            }
            _ if key == INPUT.up && is_turn_blocked(0, -1, &mut gs.ecs) == true => {
                try_move_player(0, -1, &mut gs.ecs)
            }
            _ if key == INPUT.right && is_turn_blocked(1, 0, &mut gs.ecs) == true => {
                try_move_player(1, 0, &mut gs.ecs)
            }

            _ if key == INPUT.pick_up => get_item(&mut gs.ecs),
            _ if key == INPUT.inventory => return RunState::ShowInventory { selection: 0 },

            _ if hotkeys.contains(&key) => use_hotkey(&mut gs.ecs, key),
            // cast_spell(&mut gs.ecs),
            _ if key == INPUT.select => {
                // refactor to be context-dependant on tile
                if map::try_next_level(&mut gs.ecs) {
                    return RunState::NextLevel;
                }
            }

            _ if key == INPUT.exit => {
                return RunState::MainMenu {
                    game_started: true,
                    menu_selection: gui::MainMenuSelection::NewGame,
                }
            }

            _ if key == INPUT.wait => return RunState::PlayerTurn,

            _ => return RunState::AwaitingInput,
        },
    }
    RunState::PlayerTurn
}
