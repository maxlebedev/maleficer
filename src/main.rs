use rltk::{GameState, Point, Rltk};
use specs::prelude::*;
use specs::saveload::{SimpleMarker, SimpleMarkerAllocator};

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
mod camera;
mod config;
pub mod map_builders;
mod raws;
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
        radius: i32,
    },
    MainMenu {
        game_started: bool,
        menu_selection: gui::MainMenuSelection,
    },
    NextLevel,
}

pub struct Colors {
    pub orange: rltk::RGB,
    pub black: rltk::RGB,
    pub red: rltk::RGB,
    pub yellow: rltk::RGB,
    pub magenta: rltk::RGB,
    pub cyan: rltk::RGB,
    pub dark_cyan: rltk::RGB,
    pub green: rltk::RGB,
    pub blue: rltk::RGB,
    pub white: rltk::RGB,
    pub grey: rltk::RGB,
    pub dark_grey: rltk::RGB,
}

lazy_static! {
    pub static ref COLORS: Colors = Colors {
        orange: rltk::RGB::named(rltk::ORANGE),
        black: rltk::RGB::named(rltk::BLACK),
        red: rltk::RGB::named(rltk::RED),
        yellow: rltk::RGB::named(rltk::YELLOW),
        magenta: rltk::RGB::named(rltk::MAGENTA),
        cyan: rltk::RGB::named(rltk::CYAN),
        dark_cyan: rltk::RGB::named(rltk::DARK_CYAN),
        green: rltk::RGB::named(rltk::GREEN),
        blue: rltk::RGB::named(rltk::BLUE),
        white: rltk::RGB::named(rltk::WHITE),
        grey: rltk::RGB::named(rltk::GREY),
        dark_grey: rltk::RGB::named(rltk::DARK_GREY),
    };
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
        systems::particle::cull_dead_particles(&mut self.ecs, ctx);

        match newrunstate {
            RunState::MainMenu { .. } => {}
            _ => {
                camera::render_camera(&self.ecs, ctx);
                gui::draw_char_ui(&self.ecs, ctx);
                gui::draw_world_ui(&self.ecs, ctx);
            }
        }

        match newrunstate {
            RunState::MainMenu {
                game_started,
                menu_selection: _,
            } => {
                let result = gui::main_menu(self, ctx);
                match result {
                    gui::MainMenuResult::NoSelection { selected } => {
                        newrunstate = RunState::MainMenu {
                            game_started,
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
                            if !game_started {
                                // If in game, exit menu
                                if !save_exists {
                                    // if no save exists, new game
                                    dbg!("save don't exist, making new game");
                                    newrunstate = RunState::CharGen { selection: 0 };
                                } else {
                                    // load
                                    systems::save_load::load_game(&mut self.ecs);
                                    systems::save_load::delete_save();
                                }
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
                {
                    let mut gamelog = self.ecs.fetch_mut::<gamelog::GameLog>();
                    gamelog.entries.clear();
                }
                let (menu_result, ch_selection) = gui::chargen_menu(self, ctx, selection);
                match menu_result {
                    gui::MenuAction::Cancel => {
                        newrunstate = RunState::MainMenu {
                            game_started: false,
                            menu_selection: gui::MainMenuSelection::NewGame,
                        };
                    }
                    gui::MenuAction::NoResponse => {}
                    gui::MenuAction::Up => {
                        newrunstate = RunState::CharGen {
                            selection: selection - 1,
                        }
                    }
                    gui::MenuAction::Down => {
                        newrunstate = RunState::CharGen {
                            selection: selection + 1,
                        }
                    }
                    gui::MenuAction::Selected => {
                        println!("selected {}", gui::SCHOOLS[ch_selection.unwrap()]);
                        newrunstate = RunState::PreRun {};
                    }
                    _ => {}
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
            RunState::NextLevel => {
                self.goto_next_level();
                self.run_systems();
                self.ecs.maintain();
                newrunstate = RunState::AwaitingInput;
            }

            RunState::ShowInventory { selection } => {
                let result = gui::show_inventory(self, ctx, selection);
                match result.0 {
                    gui::MenuAction::Cancel => newrunstate = RunState::AwaitingInput,
                    gui::MenuAction::NoResponse => {}
                    gui::MenuAction::Up => {
                        newrunstate = RunState::ShowInventory {
                            selection: selection - 1,
                        }
                    }
                    gui::MenuAction::Down => {
                        newrunstate = RunState::ShowInventory {
                            selection: selection + 1,
                        }
                    }
                    gui::MenuAction::Selected => {
                        let item_entity = result.1.unwrap();
                        let is_ranged = self.ecs.read_storage::<Ranged>();
                        let is_item_ranged = is_ranged.get(item_entity);
                        if let Some(is_item_ranged) = is_item_ranged {
                            let is_aoe = self.ecs.read_storage::<AreaOfEffect>();
                            let radius = match is_aoe.get(item_entity) {
                                Some(is_item_aoe) => is_item_aoe.radius,
                                None => 0,
                            };
                            newrunstate = RunState::ShowTargeting {
                                range: is_item_ranged.range,
                                item: item_entity,
                                radius,
                            };

                            //this is: fn reset_cursor_pos
                            let player_pos = self.ecs.fetch::<Point>();
                            let mut cursor = self.ecs.fetch_mut::<Cursor>();
                            cursor.point = camera::tile_to_screen(&self.ecs, *player_pos);
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
                    gui::MenuAction::Drop => {
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
            RunState::ShowTargeting {
                range,
                item,
                radius,
            } => {
                let result = gui::ranged_target(&mut self.ecs, ctx, range, radius);
                match result {
                    gui::MenuAction::Cancel => newrunstate = RunState::AwaitingInput,
                    gui::MenuAction::Selected => {
                        let mut intent = self.ecs.write_storage::<WantsToUseItem>();
                        let cursor = self.ecs.fetch::<Cursor>();
                        // TODO: should screen_to_tile be an impl in cursor?
                        let target = camera::screen_to_tile(&self.ecs, cursor.point);
                        intent
                            .insert(
                                *self.ecs.fetch::<Entity>(),
                                WantsToUseItem {
                                    item,
                                    target: Some(target),
                                },
                            )
                            .expect("Unable to insert intent");
                        newrunstate = RunState::PlayerTurn;
                    }
                    _ => {}
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
        let mut particles = systems::particle::ParticleSpawn {};
        particles.run_now(&self.ecs);

        self.ecs.maintain();
    }

    fn new_game(&mut self) {
        self.ecs.delete_all();

        let mut builder = map_builders::random_builder(1, 100, 100);
        let start;
        builder.build_map();
        {
            let mut worldmap_resource = self.ecs.write_resource::<Map>();
            *worldmap_resource = builder.get_map();
        }
        start = builder.get_starting_position();


        let (player_x, player_y) = (start.x, start.y);

        builder.spawn_entities(&mut self.ecs);

        // TODO: consider making this its own function?
        let player_entity = spawner::player(&mut self.ecs, player_x, player_y);
        self.ecs.insert(player_entity);

        self.ecs.insert(Cursor {
            point: Point::new(player_x, player_y),
        });

        self.ecs.insert(Point::new(player_x, player_y));
    }

    // TODO: we would have to edit this every time we add a player-thing.
    // better to instead remove mobs, map, uncollected items
    fn entities_to_remove_on_level_change(&mut self) -> Vec<Entity> {
        let entities = self.ecs.entities();
        let player = self.ecs.read_storage::<Player>();
        let backpack = self.ecs.read_storage::<InBackpack>();
        let player_entity = self.ecs.fetch::<Entity>();

        let mut to_delete: Vec<Entity> = Vec::new();
        for entity in entities.join() {
            let mut should_delete = true;

            // Don't delete the player
            let p = player.get(entity);
            if let Some(_p) = p {
                should_delete = false;
            }

            // Don't delete the player's equipment
            let bp = backpack.get(entity);
            if let Some(bp) = bp {
                if bp.owner == *player_entity {
                    should_delete = false;
                }
            }

            if should_delete {
                to_delete.push(entity);
            }
        }
        to_delete
    }
    // TODO: understand this
    fn goto_next_level(&mut self) {
        // Delete entities that aren't the player or his/her equipment
        let to_delete = self.entities_to_remove_on_level_change();
        for target in to_delete {
            self.ecs
                .delete_entity(target)
                .expect("Unable to delete entity");
        }

        // Build a new map and place the player
        let mut builder;
        let player_start;
        {
            let mut worldmap_resource = self.ecs.write_resource::<Map>();
            let current_depth = worldmap_resource.depth;
            builder = map_builders::random_builder(current_depth + 1, 100, 100);
            builder.build_map();
            *worldmap_resource = builder.get_map();
            player_start = builder.get_starting_position();
        }

        builder.spawn_entities(&mut self.ecs);

        // Place the player and update resources
        let (player_x, player_y) = (player_start.x, player_start.y);
        let mut player_position = self.ecs.write_resource::<Point>();
        *player_position = Point::new(player_x, player_y);

        let mut position_components = self.ecs.write_storage::<Position>();
        let player_entity = self.ecs.fetch::<Entity>();
        let player_pos_comp = position_components.get_mut(*player_entity);
        if let Some(player_pos_comp) = player_pos_comp {
            player_pos_comp.x = player_x;
            player_pos_comp.y = player_y;
        }

        // Mark the player's visibility as dirty
        let mut viewshed_components = self.ecs.write_storage::<Viewshed>();
        let vs = viewshed_components.get_mut(*player_entity);
        if let Some(vs) = vs {
            vs.dirty = true;
        }

        // Notify the player and give them some health
        let mut gamelog = self.ecs.fetch_mut::<gamelog::GameLog>();
        gamelog
            .entries
            .push("You descend to the next level, and take a moment to heal.".to_string());
        let mut player_health_store = self.ecs.write_storage::<CombatStats>();
        let player_health = player_health_store.get_mut(*player_entity);
        if let Some(player_health) = player_health {
            player_health.hp = i32::max(player_health.hp, player_health.max_hp / 2);
        }
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
    gs.ecs.register::<ParticleLifetime>();
    gs.ecs.register::<Antagonistic>();
    gs.ecs.register::<Hidden>();

    gs.ecs.insert(SimpleMarkerAllocator::<SerializeMe>::new());
    gs.ecs.insert(rltk::RandomNumberGenerator::new());

    let player_entity = spawner::player(&mut gs.ecs, 0, 0);
    gs.ecs.insert(player_entity);
    gs.ecs.insert(Point::new(0, 0));
    gs.ecs.insert(Cursor {
        point: Point::new(0, 0),
    });
}

fn main() -> rltk::BError {
    use rltk::RltkBuilder;

    let rb = RltkBuilder::simple(config::BOUNDS.win_width, config::BOUNDS.win_height);

    let context: Rltk = rb
        .unwrap()
        .with_title("Maleficer")
        .with_tile_dimensions(8, 8)
        .build()?;

    let mut gs = State { ecs: World::new() };
    gs.ecs.insert(RunState::MainMenu {
        game_started: false,
        menu_selection: gui::MainMenuSelection::NewGame,
    });

    register_all(&mut gs);

    raws::load_raws();

    let map = Map::new(1, 1, 1);
    gs.ecs.insert(map);

    let gamelog = GameLog {
        entries: vec!["Welcome to Maleficer".to_string()],
    };
    gs.ecs.insert(gamelog);

    gs.ecs.insert(systems::particle::ParticleBuilder::new());
    rltk::main_loop(context, gs)
}

#[cfg(test)]
mod tests {
    use crate::*;

    #[test]
    fn test_register() {
        let mut test_state = State { ecs: World::new() };
        register_all(&mut test_state);
    }
}
