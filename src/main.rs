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
mod config;
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
                                    self.insert_dummies();
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
                let (menu_result, ch_selection) = gui::chargen_menu(self, ctx, selection);
                match menu_result {
                    gui::SelectMenuResult::Cancel => {
                        newrunstate = RunState::MainMenu {
                            game_started: false,
                            menu_selection: gui::MainMenuSelection::NewGame,
                        };
                    }
                    gui::SelectMenuResult::NoResponse => {}
                    gui::SelectMenuResult::Up => {
                        newrunstate = RunState::CharGen {
                            selection: selection - 1,
                        }
                    }
                    gui::SelectMenuResult::Down => {
                        newrunstate = RunState::CharGen {
                            selection: selection + 1,
                        }
                    }
                    gui::SelectMenuResult::Selected => {
                        println!("selected {}", gui::SCHOOLS[ch_selection.unwrap()]);
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
            RunState::NextLevel => {
                self.goto_next_level();
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
                            selection: selection - 1,
                        }
                    }
                    gui::ItemMenuResult::Down => {
                        newrunstate = RunState::ShowInventory {
                            selection: selection + 1,
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
        let mut particles = systems::particle::ParticleSpawn {};
        particles.run_now(&self.ecs);

        self.ecs.maintain();
    }

    fn new_game(&mut self) {
        self.ecs.delete_all();
        let map = Map::new_map_rooms_and_corridors(1);
        let (player_x, player_y) = map.rooms[0].center();

        for room in map.rooms.iter().skip(1) {
            spawner::spawn_room(&mut self.ecs, room, map.depth);
        }
        self.ecs.insert(map);

        let player_entity = spawner::player(&mut self.ecs, player_x, player_y);
        self.ecs.insert(player_entity);

        self.ecs.insert(Cursor {
            point: Point::new(player_x, player_y),
        });

        self.ecs.insert(Point::new(player_x, player_y));
    }

    fn insert_dummies(&mut self) {
        let player_entity = spawner::player(&mut self.ecs, 0, 0);
        self.ecs.insert(player_entity);
        self.ecs.insert(Point::new(0, 0));
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
        let worldmap;
        {
            let mut worldmap_resource = self.ecs.write_resource::<Map>();
            let current_depth = worldmap_resource.depth;
            *worldmap_resource = Map::new_map_rooms_and_corridors(current_depth + 1);
            worldmap = worldmap_resource.clone();
        }

        // Spawn bad guys
        for room in worldmap.rooms.iter().skip(1) {
            spawner::spawn_room(&mut self.ecs, room, worldmap.depth);
        }

        // Place the player and update resources
        let (player_x, player_y) = worldmap.rooms[0].center();
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
}

fn main() -> rltk::BError {
    use rltk::RltkBuilder;

    let rb = RltkBuilder::simple(config::CONFIG.width, config::CONFIG.height);

    let mut context: Rltk = rb.unwrap().with_title("Malefactor").build()?;
    context.screen_burn_color(rltk::RGB::named(rltk::DARKGRAY));

    context.with_post_scanlines(true);
    let mut gs = State { ecs: World::new() };
    gs.ecs.insert(RunState::MainMenu {
        game_started: false,
        menu_selection: gui::MainMenuSelection::NewGame,
    });
    register_all(&mut gs);

    gs.ecs.insert(SimpleMarkerAllocator::<SerializeMe>::new());
    gs.ecs.insert(rltk::RandomNumberGenerator::new());

    raws::load_raws();

    let map = Map::dummy_map();
    gs.ecs.insert(map);

    let gamelog = GameLog {
        entries: vec!["Welcome to Malefactor".to_string()],
    };
    gs.ecs.insert(gamelog);

    gs.ecs.insert(systems::particle::ParticleBuilder::new());

    rltk::main_loop(context, gs)
}
