use rltk::{Rltk, RGB};

// TODO: we make assumptions about screen size
const MAX_X: i32 = 80;
const MAX_Y: i32 = 50;

// TODO: there are rendering issues around entities interacting
// this might be related to crossterm
#[derive(PartialEq, Copy, Clone)]
pub enum TileType {
    Wall, Floor
}

pub fn xy_idx(x: i32, y: i32) -> usize {
    ((y * MAX_X ) + x) as usize
}

/// Makes a map with solid boundaries and 400 randomly placed walls. No guarantees that it won't
/// look awful.
pub fn new_map_test() -> Vec<TileType> {
    let mut map = vec![TileType::Floor; (MAX_X*MAX_Y) as usize];

    // Make the boundaries walls
    for x in 0..MAX_X {
        map[xy_idx(x, 0)] = TileType::Wall;
        map[xy_idx(x, MAX_Y-1)] = TileType::Wall;
    }
    for y in 0..MAX_Y {
        map[xy_idx(0, y)] = TileType::Wall;
        map[xy_idx(MAX_X-1, y)] = TileType::Wall;
    }

    // Now we'll randomly splat a bunch of walls. It won't be pretty, but it's a decent illustration.
    // First, obtain the thread-local RNG:
    let mut rng = rltk::RandomNumberGenerator::new();

    for _i in 0..400 {
        let x = rng.roll_dice(1, MAX_X-1); // TODO: why are these not starting with 0?
        let y = rng.roll_dice(1, MAX_Y-1);
        let idx = xy_idx(x, y);
        if idx != xy_idx(40, 25) {
            map[idx] = TileType::Wall;
        }
        // map[idx] = TileType::Wall;
    }
    //map[xy_idx(40, 25)] = TileType::Floor;

    map
}

pub fn draw_map(map: &[TileType], ctx : &mut Rltk) {
    let mut y = 0;
    let mut x = 0;
    for tile in map.iter() {
        // Render a tile depending upon the tile type
        match tile {
            TileType::Floor => {
                ctx.set(x, y, RGB::from_f32(0.5, 0.5, 0.5), RGB::from_f32(0., 0., 0.), rltk::to_cp437('.'));
            }
            TileType::Wall => {
                ctx.set(x, y, RGB::from_f32(0.0, 1.0, 0.0), RGB::from_f32(0., 0., 0.), rltk::to_cp437('#'));
            }
        }

        // Move the coordinates
        // TODO: surely a modulo works here?
        x += 1;
        if x > 79 {
            x = 0;
            y += 1;
        }
    }
}
