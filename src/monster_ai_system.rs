use specs::prelude::*;
use super::{Viewshed, Monster, Name, map, Position};
use rltk::{Point, console};

pub struct MonsterAI {}

impl<'a> System<'a> for MonsterAI {
    #[allow(clippy::type_complexity)]
    type SystemData = ( WriteExpect<'a, map::Map>,
                        ReadExpect<'a, Point>,
                        WriteStorage<'a, Viewshed>,
                        ReadStorage<'a, Monster>,
                        ReadStorage<'a, Name>,
                        WriteStorage<'a, Position>);

    fn run(&mut self, data : Self::SystemData) {
        let (mut map, player_pos, mut viewshed, monster, name, mut position) = data;

        for (mut viewshed,_monster,name,mut pos) in (&mut viewshed, &monster, &name, &mut position).join() {
            // TODO; if I ever walk over an enemy, they stick under me forever
            if viewshed.visible_tiles.contains(&*player_pos) {
                let distance = rltk::DistanceAlg::Pythagoras.distance2d(Point::new(pos.x, pos.y), *player_pos);
                if distance < 1.5{
                    //attack goes here
                    console::log(&format!("{} shouts insults", name.name));
                    return;
                }
                let path = rltk::a_star_search(
                    map.xy_idx(pos.x, pos.y) as i32,
                    map.xy_idx(player_pos.x, player_pos.y) as i32,
                    &mut *map
                );
                if path.success && path.steps.len()>2 {
                    pos.x = path.steps[1] as i32 % map.width;
                    pos.y = path.steps[1] as i32 / map.width;
                    let idx = map.xy_idx(pos.x, pos.y);
                    map.blocked[idx] = true;
                    viewshed.dirty = true;
                }
            }
        }
    }
}
