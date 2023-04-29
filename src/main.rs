use rltk::{GameState, Point, Rltk};
use specs::prelude::*;
use specs::saveload::{SimpleMarker, SimpleMarkerAllocator};
use std::cmp::{max, min};

#[macro_use]
extern crate lazy_static;

mod map;
pub use map::*;
mod player;
pub use player::*;
mod components;
pub use components::*;
mod gamelog;
mod gui;
mod rect;
mod systems;
pub use gamelog::GameLog;
mod config;
mod spawner;

#[derive(PartialEq, Copy, Clone)]
pub enum RunState {
    AwaitingInput,
    PreRun,
    CharGen {
        selection: usize,
    },
    PlayerTurn,
    MonsterTurn,
    ShowInventory {
        selection: usize,
    },
    ShowTargeting {
        range: i32,
        item: Entity,
    },
    MainMenu {
        menu_selection: gui::MainMenuSelection,
    },
}

pub struct State {
    ecs: World,
}

impl GameState for State {
    fn tick(&mut self, ctx: &mut Rltk) {
        let mut newrunstate;
        {
            let runstate = self.ecs.fetch::<RunState>();
            newrunstate = *runstate;
        }
        ctx.cls();

        match newrunstate {
            RunState::MainMenu { .. } => {}
            _ => {
                draw_map(&self.ecs, ctx);

                {
                    let positions = self.ecs.read_storage::<Position>();
                    let renderables = self.ecs.read_storage::<Renderable>();
                    let map = self.ecs.fetch::<Map>();

                    let mut data = (&positions, &renderables).join().collect::<Vec<_>>();
                    data.sort_by(|&a, &b| b.1.render_order.cmp(&a.1.render_order));
                    for (pos, render) in data.iter() {
                        let idx = map.xy_idx(pos.x, pos.y);
                        if map.visible_tiles[idx] {
                            ctx.set(pos.x, pos.y, render.fg, render.bg, render.glyph)
                        }
                    }

                    gui::draw_ui(&self.ecs, ctx);
                }
            }
        }

        match newrunstate {
            RunState::MainMenu { .. } => {
                let result = gui::main_menu(self, ctx);
                match result {
                    gui::MainMenuResult::NoSelection { selected } => {
                        newrunstate = RunState::MainMenu {
                            menu_selection: selected,
                        }
                    }
                    gui::MainMenuResult::Selected { selected } => match selected {
                        gui::MainMenuSelection::NewGame => {
                            newrunstate = RunState::CharGen { selection: 0 }
                        }
                        gui::MainMenuSelection::Continue => {
                            let save_exists = systems::save_load::does_save_exist();
                            newrunstate = RunState::AwaitingInput;
                            if !self.ecs.has_value::<Player>() {
                                newrunstate = RunState::CharGen { selection: 0 };
                            }
                            if save_exists {
                                systems::save_load::load_game(&mut self.ecs);
                                systems::save_load::delete_save();
                            }
                        }
                        gui::MainMenuSelection::Quit => {
                            systems::save_load::save_game(&mut self.ecs);
                            ::std::process::exit(0);
                        }
                    },
                }
            }
            RunState::CharGen { selection } => {
                let (menu_result, th_selection) = gui::chargen_menu(self, ctx, selection);
                match menu_result {
                    gui::SelectMenuResult::Cancel => {
                        newrunstate = RunState::MainMenu {
                            menu_selection: gui::MainMenuSelection::NewGame,
                        };
                    }
                    gui::SelectMenuResult::NoResponse => {}
                    gui::SelectMenuResult::Up => {
                        newrunstate = RunState::CharGen {
                            selection: max(selection - 1, 0),
                        }
                    }
                    gui::SelectMenuResult::Down => {
                        newrunstate = RunState::CharGen {
                            selection: min(selection + 1, 20),
                        }
                    }
                    gui::SelectMenuResult::Selected => {
                        println!("selected {}", gui::SCHOOLS[th_selection.unwrap()]);
                        newrunstate = RunState::PreRun {};
                    }
                }
            }
            RunState::PreRun => {
                self.new_game();
                player::make_character(&mut self.ecs);
                self.run_systems();
                self.ecs.maintain();
                newrunstate = RunState::AwaitingInput;
            }
            RunState::AwaitingInput => {
                newrunstate = player_input(self, ctx);
            }
            RunState::PlayerTurn => {
                self.run_systems();
                self.ecs.maintain();
                newrunstate = RunState::MonsterTurn;
            }
            RunState::MonsterTurn => {
                self.run_systems();
                self.ecs.maintain();
                newrunstate = RunState::AwaitingInput;
            }
            RunState::ShowInventory { selection } => {
                let result = gui::show_inventory(self, ctx, selection);
                match result.0 {
                    gui::ItemMenuResult::Cancel => newrunstate = RunState::AwaitingInput,
                    gui::ItemMenuResult::NoResponse => {}
                    gui::ItemMenuResult::Up => {
                        newrunstate = RunState::ShowInventory {
                            selection: max(selection - 1, 0),
                        }
                    }
                    gui::ItemMenuResult::Down => {
                        newrunstate = RunState::ShowInventory {
                            selection: min(selection + 1, 20),
                        }
                    }
                    gui::ItemMenuResult::Selected => {
                        let item_entity = result.1.unwrap();
                        let is_ranged = self.ecs.read_storage::<Ranged>();
                        let is_item_ranged = is_ranged.get(item_entity);
                        if let Some(is_item_ranged) = is_item_ranged {
                            newrunstate = RunState::ShowTargeting {
                                range: is_item_ranged.range,
                                item: item_entity,
                            };

                            //this is: fn reset_cursor_pos
                            let player_pos = self.ecs.fetch::<Point>();
                            let mut cursor = self.ecs.fetch_mut::<Cursor>();
                            cursor.point = *player_pos;
                        } else {
                            let mut intent = self.ecs.write_storage::<WantsToUseItem>();
                            intent
                                .insert(
                                    *self.ecs.fetch::<Entity>(),
                                    WantsToUseItem {
                                        item: item_entity,
                                        target: None,
                                    },
                                )
                                .expect("Unable to insert intent");
                            newrunstate = RunState::PlayerTurn;
                        }
                    }
                    gui::ItemMenuResult::Drop => {
                        let item_entity = result.1.unwrap();
                        let mut intent = self.ecs.write_storage::<WantsToDropItem>();
                        intent
                            .insert(
                                *self.ecs.fetch::<Entity>(),
                                WantsToDropItem { item: item_entity },
                            )
                            .expect("Unable to insert intent");
                        newrunstate = RunState::PlayerTurn;
                    }
                }
            }
            RunState::ShowTargeting { range, item } => {

                let result = gui::ranged_target(&mut self.ecs, ctx, range);
                match result {
                    gui::SelectResult::Cancel => newrunstate = RunState::AwaitingInput,
                    gui::SelectResult::NoResponse => {}
                    gui::SelectResult::Selected => {
                        let mut intent = self.ecs.write_storage::<WantsToUseItem>();
                        let cursor = self.ecs.fetch::<Cursor>();
                        intent
                            .insert(
                                *self.ecs.fetch::<Entity>(),
                                WantsToUseItem {
                                    item,
                                    target: Some(cursor.point),
                                },
                            )
                            .expect("Unable to insert intent");
                        newrunstate = RunState::PlayerTurn;
                    }
                }
            }
        }
        {
            let mut runwriter = self.ecs.write_resource::<RunState>();
            *runwriter = newrunstate;
        }
        systems::damage::delete_the_dead(&mut self.ecs);
    }
}

impl State {
    fn run_systems(&mut self) {
        let mut vis = systems::visibility::Visibility {};
        vis.run_now(&self.ecs);
        let mut mob = systems::monster_ai::MonsterAI {};
        mob.run_now(&self.ecs);
        let mut mapindex = systems::map_indexing::MapIndexing {};
        mapindex.run_now(&self.ecs);
        let mut melee = systems::melee_combat::MeleeCombat {};
        melee.run_now(&self.ecs);
        let mut damage = systems::damage::Damage {};
        damage.run_now(&self.ecs);
        let mut pickup = systems::item::ItemCollection {};
        pickup.run_now(&self.ecs);
        let mut items = systems::item::ItemUse {};
        items.run_now(&self.ecs);
        let mut drop_items = systems::item::ItemDrop {};
        drop_items.run_now(&self.ecs);

        self.ecs.maintain();
    }

    fn new_game(&mut self) {
        self.ecs.delete_all();
        let map = Map::new_map_rooms_and_corridors();
        let (player_x, player_y) = map.rooms[0].center();

        for room in map.rooms.iter().skip(1) {
            spawner::spawn_room(&mut self.ecs, room);
        }
        self.ecs.insert(map);

        let player_entity = spawner::player(&mut self.ecs, player_x, player_y);
        self.ecs.insert(player_entity);

        self.ecs.insert(Cursor {
            point: Point::new(player_x, player_y),
        });

        self.ecs.insert(Point::new(player_x, player_y));
    }
}

fn register_all(gs: &mut State) {
    gs.ecs.register::<Position>();
    gs.ecs.register::<Renderable>();
    gs.ecs.register::<Player>();
    gs.ecs.register::<Viewshed>();
    gs.ecs.register::<Monster>();
    gs.ecs.register::<Name>();
    gs.ecs.register::<BlocksTile>();
    gs.ecs.register::<CombatStats>();
    gs.ecs.register::<WantsToMelee>();
    gs.ecs.register::<SufferDamage>();
    gs.ecs.register::<Item>();
    gs.ecs.register::<ProvidesHealing>();
    gs.ecs.register::<InBackpack>();
    gs.ecs.register::<WantsToPickupItem>();
    gs.ecs.register::<WantsToUseItem>();
    gs.ecs.register::<WantsToDropItem>();
    gs.ecs.register::<Consumable>();
    gs.ecs.register::<Ranged>();
    gs.ecs.register::<InflictsDamage>();
    gs.ecs.register::<AreaOfEffect>();
    gs.ecs.register::<SimpleMarker<SerializeMe>>();
    gs.ecs.register::<SerializationHelper>();
    gs.ecs.register::<SerializationHelper>();
    gs.ecs.register::<Cursor>();
    gs.ecs.register::<Spell>();
    gs.ecs.register::<WantsToCastSpell>();
}

fn main() -> rltk::BError {
    use rltk::RltkBuilder;

    let rb = RltkBuilder::simple(config::CONFIG.width, config::CONFIG.height);

    let mut context: Rltk = rb.unwrap().with_title("Malefactor").build()?;
    context.screen_burn_color(rltk::RGB::named(rltk::DARKGRAY));

    context.with_post_scanlines(true);
    let mut gs = State { ecs: World::new() };
    gs.ecs.insert(RunState::MainMenu {
        menu_selection: gui::MainMenuSelection::NewGame,
    });
    register_all(&mut gs);

    gs.ecs.insert(SimpleMarkerAllocator::<SerializeMe>::new());
    gs.ecs.insert(rltk::RandomNumberGenerator::new());

    let map = Map::dummy_map();
    gs.ecs.insert(map);

    let gamelog = GameLog {
        entries: vec!["Welcome to Malefactor".to_string()],
    };
    gs.ecs.insert(gamelog);

    rltk::main_loop(context, gs)
}
