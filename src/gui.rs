use rltk::{ RGB, Rltk, VirtualKeyCode };
use specs::prelude::*;

use super::{components, Player, GameLog, State};
use super::map::{MAPWIDTH, MAPHEIGHT};
pub use components::*;

pub fn draw_ui(ecs: &World, ctx : &mut Rltk) {
    ctx.draw_box(0, MAPHEIGHT, MAPWIDTH-1, 6, RGB::named(rltk::WHITE), RGB::named(
        rltk::BLACK));

    let combat_stats = ecs.read_storage::<CombatStats>();
    let players = ecs.read_storage::<Player>();
    for (_player, stats) in (&players, &combat_stats).join() {
        let health = format!(" HP: {} / {} ", stats.hp, stats.max_hp);
        ctx.print_color(12, MAPWIDTH, RGB::named(rltk::YELLOW), RGB::named(rltk::BLACK), &health);

        ctx.draw_bar_horizontal(28, MAPHEIGHT, 51, stats.hp, stats.max_hp, RGB::named(rltk::RED), RGB::named(rltk::BLACK));
    }
    let log = ecs.fetch::<GameLog>();

    let mut y = 44;
    for s in log.entries.iter().rev() {
        if y < 49 { ctx.print(2, y, s); }
        y += 1;
    }
}

#[derive(PartialEq, Copy, Clone)]
pub enum ItemMenuResult { Cancel, NoResponse, Selected }

// TODO: strongly consider a full-screen inventory thing
pub fn show_inventory(gs : &mut State, ctx : &mut Rltk) -> (ItemMenuResult, Option<Entity>) {
    let player_entity = gs.ecs.fetch::<Entity>();
    let names = gs.ecs.read_storage::<Name>();
    let backpack = gs.ecs.read_storage::<InBackpack>();
    let entities = gs.ecs.entities();

    let inventory = (&backpack, &names).join().filter(|item| item.0.owner == *player_entity );
    let count = inventory.count();

    let white = RGB::named(rltk::WHITE);
    let black = RGB::named(rltk::BLACK);
    let yellow = RGB::named(rltk::YELLOW);

    let mut y = (25 - (count / 2)) as i32;
    ctx.draw_box(15, y-2, 31, (count+3) as i32, white, black);
    ctx.print_color(18, y-2, yellow, black, "Inventory");
    ctx.print_color(18, y+count as i32+1, yellow, black, "ESCAPE to cancel");

    let mut equippable : Vec<Entity> = Vec::new();
    let mut j = 0;
    for (entity, _pack, name) in (&entities, &backpack, &names).join().filter(|item| item.1.owner == *player_entity ) {
        ctx.set(17, y, white, black, rltk::to_cp437('('));
        ctx.set(18, y, yellow, black, 97+j as rltk::FontCharType);
        ctx.set(19, y, white, black, rltk::to_cp437(')'));

        ctx.print(21, y, &name.name.to_string());
        equippable.push(entity);
        y += 1;
        j += 1;
    }

    match ctx.key {
        None => (ItemMenuResult::NoResponse, None),
        Some(key) => {
            match key {
                VirtualKeyCode::Escape => { (ItemMenuResult::Cancel, None) }
                _ => {
                    let selection = rltk::letter_to_option(key);
                    if selection > -1 && selection < count as i32 {
                        return (ItemMenuResult::Selected, Some(equippable[selection as usize]));
                    }  
                    (ItemMenuResult::NoResponse, None)
                }
            }
        }
    }
}
