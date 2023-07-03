use std::collections::HashMap;

use rltk::RGB;
use serde::{Deserialize, Serialize};
use bevy::prelude::*;

#[derive(Component, Clone)]
pub struct Position {
    pub x: i32,
    pub y: i32,
}

#[derive(Component, Clone)]
pub struct Renderable {
    pub glyph: rltk::FontCharType,
    pub fg: RGB,
    pub bg: RGB,
    pub render_order: i32,
}

#[derive(Component, Serialize, Deserialize, Clone)]
pub struct Player {}

#[derive(Component, Clone)]
pub struct Viewshed {
    pub visible_tiles: Vec<rltk::Point>,
    pub range: i32,
    pub dirty: bool,
}

#[derive(Component, Debug, Serialize, Deserialize, Clone)]
pub struct Monster {}

/* Bevy gives us one of these
#[derive(Component, Debug, Clone)]
pub struct Name {
    pub name: String,
}*/

#[derive(Component, Debug, Serialize, Deserialize, Clone)]
pub struct BlocksTile {}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct Pool {
    pub max: i32,
    pub current: i32,
}

#[derive(Component, Debug, Clone)]
pub struct EntityStats {
    // As opposed to stats for a run or w.e
    pub defense: i32,
    pub power: i32,
    pub pools: HashMap<String, Pool>,
}

impl EntityStats {
    pub fn get(&self, stat: &str) -> (i32, i32) {
        match self.pools.get(stat) {
            Some(stat_pool) => (stat_pool.current, stat_pool.max),
            _ => (0, 0),
        }
    }
    pub fn set_current(&mut self, key: &str, value: i32) {
        let mut pool = self.pools.get_mut(key).unwrap();
        pool.current = value;
    }

    pub fn set_max(&mut self, key: &str, value: i32) {
        let mut pool = self.pools.get_mut(key).unwrap();
        pool.max = value;
    }

    pub fn deplete(&mut self, key: &str, value: i32) {
        let mut pool = self.pools.get_mut(key).unwrap();
        pool.current -= value;
    }

    pub fn restore(&mut self, key: &str, value: i32) {
        let mut pool = self.pools.get_mut(key).unwrap();
        pool.current = std::cmp::min(pool.current + value, pool.max);
    }
}

#[derive(Component, Debug, Clone)]
pub struct WantsToMelee {
    pub target: Entity,
}

#[derive(Component, Debug, Serialize, Deserialize, Clone)]
pub struct Item {}

#[derive(Component, Debug, Serialize, Deserialize, Clone)]
pub struct Destructable {}

#[derive(Component, Debug, Serialize, Deserialize, Clone)]
pub struct Consumable {}

#[derive(Component, Debug, Serialize, Deserialize, Clone)]
pub struct SingleActivation {}

#[derive(Component, Debug, Clone)]
pub struct Ranged {
    pub range: i32,
}

#[derive(Component, Debug, Clone)]
pub struct InflictsDamage {
    pub damage: i32,
}

#[derive(Component, Debug, Clone)]
pub struct AreaOfEffect {
    pub radius: i32,
}

/*
#[derive(Component, Debug, Clone)]
pub struct Confusion {
    pub turns : i32
}
*/

#[derive(Component, Debug, Clone)]
pub struct ProvidesHealing {
    pub heal_amount: i32,
}

#[derive(Component, Debug, Clone)]
pub struct ProvidesMana{
    pub mana_amount: i32,
}

#[derive(Component, Debug, Clone)]
pub struct CostsMana{
    pub mana_amount: i32,
}

#[derive(Component, Debug)]
pub struct InBackpack {
    pub owner: Entity,
}

#[derive(Component, Debug)]
pub struct WantsToPickupItem {
    pub collected_by: Entity,
    pub item: Entity,
}

#[derive(Component, Debug)]
pub struct WantsToUseItem {
    pub item: Entity,
    pub target: Option<rltk::Point>,
}

#[derive(Component, Debug)]
pub struct WantsToDropItem {
    pub item: Entity,
}

pub struct SerializeMe;

// Special component that exists to help serialize the game data
#[derive(Component, Serialize, Deserialize, Clone)]
pub struct SerializationHelper {
    pub map: super::map::Map,
}

// Status system. Each status works in a predicable way.
// Bleed X means: take x dmg. X decreases every turn.
// there are a bunch of different types of statuses. how to model this in ECS-land?
pub struct Status {
    pub duration: i32,
    pub typ: str,
}

impl Status {
    fn _tick() {
        //
    }
}

#[derive(Component, Clone)]
pub struct Cursor {
    pub point: rltk::Point,
}

#[derive(Component, Serialize, Deserialize, Clone)]
pub struct Spell {
    pub hotkey: String,
}

#[derive(Component, Debug)]
pub struct WantsToCastSpell {
    pub source: Entity,
    pub target: Option<rltk::Point>,
}

#[derive(Component, Clone)]
pub struct ParticleLifetime {
    pub lifetime_ms: f32,
}

#[derive(Component, Serialize, Deserialize, Clone)]
pub struct Antagonistic {}

#[derive(Component, Debug, Serialize, Deserialize, Clone)]
pub struct Hidden {}

#[derive(Component, Debug, Serialize, Deserialize, Clone)]
pub struct ApplyTeleport {
    pub dest_x: i32,
    pub dest_y: i32,
}

#[derive(Component, Debug, Serialize, Deserialize, Clone)]
pub struct TeleportTo {
    pub x: i32,
    pub y: i32,
}

#[derive(Component, Serialize, Deserialize, Clone)]
pub struct SpawnParticleLine {
    pub glyph: rltk::FontCharType,
    pub color: RGB,
    pub lifetime_ms: f32,
}

#[derive(Component, Serialize, Deserialize, Clone)]
pub struct SpawnParticleBurst {
    pub glyph: rltk::FontCharType,
    pub color: RGB,
    pub lifetime_ms: f32,
}
