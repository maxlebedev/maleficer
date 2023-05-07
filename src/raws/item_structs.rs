use serde::Deserialize;
use std::collections::HashMap;

#[derive(Deserialize, Debug)]
pub struct Item {
    pub name: String,
    pub renderable: Option<Renderable>,
    pub consumable: Option<Consumable>,
    pub stats: Option<ItemStats>
}

#[derive(Deserialize, Debug)]
pub struct Renderable {
    pub glyph: String,
    pub fg: String,
    pub bg: String,
    pub order: i32,
}

#[derive(Deserialize, Debug)]
pub struct Consumable {
    pub effects: HashMap<String, String>,
}

#[derive(Deserialize, Debug)]
pub struct ItemStats {
    pub max_hp: i32,
    pub hp: i32,
}
