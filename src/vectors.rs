use std::ops::{Add, AddAssign, Div, Mul, Sub, SubAssign};

// TODO: can I just call this board and put it in /board?
#[derive(Copy, Clone, Debug, Default, PartialEq, Eq, Hash)]
pub struct Coord {
    pub x: i32,
    pub y: i32,
}

impl Coord {
    pub const UP: Coord = Coord { x: 0, y: 1 };
    pub const DOWN: Coord = Coord { x: 0, y: -1 };
    pub const LEFT: Coord = Coord { x: -1, y: 0 };
    pub const RIGHT: Coord = Coord { x: 1, y: 0 };
    pub fn new(x: i32, y: i32) -> Coord {
        Coord { x, y }
    }
    pub fn manhattan(&self, other: Coord) -> i32 {
        (self.x - other.x).abs() + (self.y - other.y).abs()
    }
}

impl Add for Coord {
    type Output = Self;

    fn add(self, other: Self) -> Self {
        return Coord::new(self.x + other.x, self.y + other.y);
    }
}

impl AddAssign for Coord {
    fn add_assign(&mut self, other: Self) {
        *self = Self {
            x: self.x + other.x,
            y: self.y + other.y,
        };
    }
}

impl Sub for Coord {
    type Output = Self;

    fn sub(self, other: Self) -> Self {
        return Coord::new(self.x - other.x, self.y - other.y);
    }
}

impl SubAssign for Coord {
    fn sub_assign(&mut self, other: Self) {
        *self = Self {
            x: self.x - other.x,
            y: self.y - other.y,
        };
    }
}

impl Div<i32> for Coord {
    type Output = Self;

    fn div(self, other: i32) -> Self {
        return Coord::new(self.x / other, self.y / other);
    }
}

impl Mul<i32> for Coord {
    type Output = Self;

    fn mul(self, other: i32) -> Self {
        return Coord::new(self.x * other, self.y * other);
    }
}

impl Mul<Coord> for i32 {
    type Output = Coord;

    fn mul(self, other: Coord) -> Coord {
        return Coord::new(other.x * self, other.y * self);
    }
}

pub const ORTHO_DIRECTIONS: [Coord; 4] = [Coord::UP, Coord::DOWN, Coord::LEFT, Coord::RIGHT];
