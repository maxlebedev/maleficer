use specs::prelude::*;
use super::{components};
use rltk::{field_of_view, Point, console};

pub struct MonsterAI {}

impl<'a> System<'a> for MonsterAI {
    type SystemData = ( ReadStorage<'a, components::Viewshed>, 
                        ReadStorage<'a, components::Position>,
                        ReadStorage<'a, components::Monster>);

    fn run(&mut self, data : Self::SystemData) {
        let (viewshed, pos, monster) = data;

        for (viewshed,pos,_monster) in (&viewshed, &pos, &monster).join() {
            console::log("Monster considers their own existence");
        }
    }
}
