use rltk::{GameState, Rltk, RGB};
use specs::prelude::*;

mod map;
mod player;
mod components;
mod rect;
mod visibility_system;
mod monster_ai_system;

#[derive(PartialEq, Copy, Clone)]
pub enum RunState { Paused, Running }

pub struct State {
    ecs: World,
}



impl GameState for State {
    fn tick(&mut self, ctx: &mut Rltk) {
        ctx.cls();

        player::player_input(self, ctx);
        self.run_systems();

        map::draw_map(&self.ecs, ctx);
        let positions = self.ecs.read_storage::<components::Position>();
        let renderables = self.ecs.read_storage::<components::Renderable>();
        let map = self.ecs.fetch::<map::Map>();

        for (pos, render) in (&positions, &renderables).join() {
            let idx = map.xy_idx(pos.x, pos.y);
            if map.visible_tiles[idx] {
                ctx.set(pos.x, pos.y, render.fg, render.bg, render.glyph);
            }
        }
    }
}

impl State {
    fn run_systems(&mut self) {
        let mut vis = visibility_system::VisibilitySystem{};
        vis.run_now(&self.ecs);
        let mut mob = monster_ai_system::MonsterAI{};
        mob.run_now(&self.ecs);
        self.ecs.maintain();
    }
}

fn main() -> rltk::BError {
    use rltk::RltkBuilder;
    let context: Rltk = RltkBuilder::simple80x50()
        .with_title("Roguelike Tutorial")
        .build()?;
    let mut gs = State { ecs: World::new() };
    gs.ecs.register::<components::Position>();
    gs.ecs.register::<components::Renderable>();
    gs.ecs.register::<components::Player>();
    gs.ecs.register::<components::Viewshed>();
    gs.ecs.register::<components::Monster>();

    let map = map::Map::new_map_rooms_and_corridors();
    let (player_x, player_y) = map.rooms[0].center();

    let mut rng = rltk::RandomNumberGenerator::new();
    for room in map.rooms.iter().skip(1) {
        let (x,y) = room.center();
        let glyph : rltk::FontCharType;
        let roll = rng.roll_dice(1, 2);
        match roll {
            1 => { glyph = rltk::to_cp437('g') }
            _ => { glyph = rltk::to_cp437('o') }
        }
        gs.ecs.create_entity()
            .with(components::Position{ x, y })
            .with(components::Renderable{
                glyph: glyph,
                fg: RGB::named(rltk::RED),
                bg: RGB::named(rltk::BLACK),
            })
            .with(components::Viewshed{ visible_tiles : Vec::new(), range: 8, dirty: true })
            .with(components::Monster{})
            .build();
    }
    gs.ecs.insert(map);

    gs.ecs
        .create_entity()
        .with(components::Position { x: player_x, y: player_y })
        .with(components::Renderable {
            glyph: rltk::to_cp437('@'),
            fg: RGB::named(rltk::YELLOW),
            bg: RGB::named(rltk::BLACK),
        })
        .with(components::Player{})
        .with(components::Viewshed{ visible_tiles : Vec::new(), range : 8, dirty : true })
        .build();


    rltk::main_loop(context, gs)
}
