use rltk::{GameState, Rltk, RGB};
use specs::prelude::*;

mod map;
// pub use map::*;
mod player;
mod components;



pub struct State {
    ecs: World,
}


impl GameState for State {
    fn tick(&mut self, ctx: &mut Rltk) {
        ctx.cls();

        player::player_input(self, ctx);
        self.run_systems();

        let the_map = self.ecs.fetch::<Vec<map::TileType>>();
        map::draw_map(&the_map, ctx);
        let positions = self.ecs.read_storage::<components::Position>();
        let renderables = self.ecs.read_storage::<components::Renderable>();

        for (pos, render) in (&positions, &renderables).join() {
            ctx.set(pos.x, pos.y, render.fg, render.bg, render.glyph);
        }
    }
}

impl State {
    fn run_systems(&mut self) {
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

    gs.ecs
        .create_entity()
        .with(components::Position { x: 40, y: 25 })
        .with(components::Renderable {
            glyph: rltk::to_cp437('@'),
            fg: RGB::named(rltk::YELLOW),
            bg: RGB::named(rltk::BLACK),
        })
        .with(components::Player{})
        .build();

    gs.ecs.insert(map::new_map_test());

    rltk::main_loop(context, gs)
}
