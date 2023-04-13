use rltk::{GameState, Rltk};
use specs::prelude::*;

mod map;
pub use map::*;
mod player;
pub use player::*;
mod components;
pub use components::*;
mod rect;
mod visibility_system;
mod monster_ai_system;
mod map_indexing_system;
mod melee_combat_system;
mod damage_system;
mod gui;
mod gamelog;
pub use gamelog::GameLog;
mod spawner;
mod inventory_system;

#[derive(PartialEq, Copy, Clone)]
pub enum RunState { 
    AwaitingInput,
    PreRun,
    PlayerTurn,
    MonsterTurn,
    ShowInventory,
}

pub struct State {
    ecs: World,
}


impl GameState for State {
    fn tick(&mut self, ctx: &mut Rltk) {
        ctx.cls();
        let mut newrunstate;
        {
            let runstate = self.ecs.fetch::<RunState>();
            newrunstate = *runstate;
        }
        match newrunstate {
            RunState::PreRun => {
                self.run_systems();
                newrunstate = RunState::AwaitingInput;
            }
            RunState::AwaitingInput => {
                newrunstate = player_input(self, ctx);
            }
            RunState::PlayerTurn => {
                self.run_systems();
                newrunstate = RunState::MonsterTurn;
            }
            RunState::MonsterTurn => {
                self.run_systems();
                newrunstate = RunState::AwaitingInput;
            }
            RunState::ShowInventory => {
                let result = gui::show_inventory(self, ctx);
                match result.0 {
                    gui::ItemMenuResult::Cancel => newrunstate = RunState::AwaitingInput,
                    gui::ItemMenuResult::NoResponse => {}
                    gui::ItemMenuResult::Selected => {
                        let item_entity = result.1.unwrap();
                        let names = self.ecs.read_storage::<Name>();
                        let mut gamelog = self.ecs.fetch_mut::<gamelog::GameLog>();
                        gamelog.entries.push(format!("You try to use {}, but it isn't written yet", names.get(item_entity).unwrap().name));
                        newrunstate = RunState::AwaitingInput;
                    }
                }
            }
        }
        {
            let mut runwriter = self.ecs.write_resource::<RunState>();
            *runwriter = newrunstate;
        }
        damage_system::delete_the_dead(&mut self.ecs);

        draw_map(&self.ecs, ctx);

        let positions = self.ecs.read_storage::<Position>();
        let renderables = self.ecs.read_storage::<Renderable>();
        let map = self.ecs.fetch::<Map>();

        for (pos, render) in (&positions, &renderables).join() {
            let idx = map.xy_idx(pos.x, pos.y);
            if map.visible_tiles[idx] { ctx.set(pos.x, pos.y, render.fg, render.bg, render.glyph) }
        }
        gui::draw_ui(&self.ecs, ctx);
    }
}

impl State {
    fn run_systems(&mut self) {
        let mut vis = visibility_system::VisibilitySystem{};
        vis.run_now(&self.ecs);
        let mut mob = monster_ai_system::MonsterAI{};
        mob.run_now(&self.ecs);
        let mut mapindex = map_indexing_system::MapIndexingSystem{};
        mapindex.run_now(&self.ecs);
        let mut melee = melee_combat_system::MeleeCombatSystem{};
        melee.run_now(&self.ecs);
        let mut damage = damage_system::DamageSystem{};
        damage.run_now(&self.ecs);
        let mut pickup = inventory_system::ItemCollectionSystem{};
        pickup.run_now(&self.ecs);

        self.ecs.maintain();
    }
}

fn main() -> rltk::BError {
    use rltk::RltkBuilder;
    let mut context: Rltk = RltkBuilder::simple80x50()
        .with_title("Roguelike Tutorial")
        .build()?;
    // TODO: figure out how to make background not black
    context.with_post_scanlines(true);
    let mut gs = State {
        ecs: World::new(),
    } ;
    gs.ecs.insert(RunState::PreRun);
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
    gs.ecs.register::<Potion>();
    gs.ecs.register::<InBackpack>();
    gs.ecs.register::<WantsToPickupItem>();

    let map = Map::new_map_rooms_and_corridors();
    let (player_x, player_y) = map.rooms[0].center();

    gs.ecs.insert(rltk::RandomNumberGenerator::new());
    for room in map.rooms.iter().skip(1) {
        spawner::spawn_room(&mut gs.ecs, room);
    }
    gs.ecs.insert(map);

    let player_entity = spawner::player(&mut gs.ecs, player_x, player_y);
    gs.ecs.insert(player_entity);

    gs.ecs.insert(rltk::Point::new(player_x, player_y));

    gs.ecs.insert(GameLog{ entries : vec!["Welcome to Rusty Roguelike".to_string()] });

    rltk::main_loop(context, gs)
}
