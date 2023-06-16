use super::Raws;
use crate::{components::*, systems::random_table::RandomTable};
use specs::saveload::MarkedBuilder;
use specs::{prelude::*, saveload::SimpleMarker};
use std::collections::{HashMap, HashSet};

pub struct RawMaster {
    raws: Raws,
    item_index: HashMap<String, usize>,
    mob_index: HashMap<String, usize>,
}

// lime_green bfff47

impl RawMaster {
    pub fn empty() -> RawMaster {
        RawMaster {
            raws: Raws {
                items: Vec::new(),
                mobs: Vec::new(),
                spawn_table: Vec::new(),
            },
            item_index: HashMap::new(),
            mob_index: HashMap::new(),
        }
    }

    pub fn load(&mut self, raws: Raws) {
        self.raws = raws;
        self.item_index = HashMap::new();
        let mut used_names: HashSet<String> = HashSet::new();
        for (i, item) in self.raws.items.iter().enumerate() {
            if used_names.contains(&item.name) {
                rltk::console::log(format!(
                    "WARNING -  duplicate item name in raws [{}]",
                    item.name
                ));
            }
            self.item_index.insert(item.name.clone(), i);
            used_names.insert(item.name.clone());
        }
        for (i, mob) in self.raws.mobs.iter().enumerate() {
            if used_names.contains(&mob.name) {
                rltk::console::log(format!(
                    "WARNING -  duplicate mob name in raws [{}]",
                    mob.name
                ));
            }
            self.mob_index.insert(mob.name.clone(), i);
            used_names.insert(mob.name.clone());
        }

        for spawn in self.raws.spawn_table.iter() {
            if !used_names.contains(&spawn.name) {
                rltk::console::log(format!(
                    "WARNING - Spawn tables references unspecified entity {}",
                    spawn.name
                ));
            }
        }
    }
}

pub enum SpawnType {
    AtPosition { x: i32, y: i32 },
}

fn spawn_position(pos: SpawnType, new_entity: EntityBuilder) -> EntityBuilder {
    let mut eb = new_entity;

    // Spawn in the specified location
    match pos {
        SpawnType::AtPosition { x, y } => {
            eb = eb.with(Position { x, y });
        }
    }

    eb
}

fn get_renderable_component(
    renderable: &super::item_structs::Renderable,
) -> crate::components::Renderable {
    crate::components::Renderable {
        glyph: rltk::to_cp437(renderable.glyph.chars().next().unwrap()),
        fg: rltk::RGB::from_hex(&renderable.fg).expect("Invalid RGB"),
        bg: rltk::RGB::from_hex(&renderable.bg).expect("Invalid RGB"),
        render_order: renderable.order,
    }
}

fn parse_particle_line(n: &str) -> SpawnParticleLine {
    let tokens: Vec<_> = n.split(';').collect();
    SpawnParticleLine {
        glyph: rltk::to_cp437(tokens[0].chars().next().unwrap()),
        color: rltk::RGB::from_hex(tokens[1]).expect("Bad RGB"),
        lifetime_ms: tokens[2].parse::<f32>().unwrap(),
    }
}

fn parse_particle(n: &str) -> SpawnParticleBurst {
    let tokens: Vec<_> = n.split(';').collect();
    SpawnParticleBurst {
        glyph: rltk::to_cp437(tokens[0].chars().next().unwrap()),
        color: rltk::RGB::from_hex(tokens[1]).expect("Bad RGB"),
        lifetime_ms: tokens[2].parse::<f32>().unwrap(),
    }
}

macro_rules! apply_effects {
    ( $effects:expr, $eb:expr ) => {
        for effect in $effects.iter() {
            let effect_name = effect.0.as_str();
            match effect_name {
                "provides_healing" => {
                    $eb = $eb.with(ProvidesHealing {
                        heal_amount: effect.1.parse::<i32>().unwrap(),
                    })
                }
                "ranged" => {
                    $eb = $eb.with(Ranged {
                        range: effect.1.parse::<i32>().unwrap(),
                    })
                }
                "damage" => {
                    $eb = $eb.with(InflictsDamage {
                        damage: effect.1.parse::<i32>().unwrap(),
                    })
                }
                "area_of_effect" => {
                    $eb = $eb.with(AreaOfEffect {
                        radius: effect.1.parse::<i32>().unwrap(),
                    })
                }
                "single_activation" => $eb = $eb.with(SingleActivation {}),
                "teleportation" => $eb = $eb.with(TeleportTo { x: 0, y: 0 }),
                "particle_line" => $eb = $eb.with(parse_particle_line(&effect.1)),
                "particle" => $eb = $eb.with(parse_particle(&effect.1)),
                "costs_mana" => {
                    $eb = $eb.with(CostsMana {
                        mana_amount: effect.1.parse::<i32>().unwrap(),
                    })
                }
                "provides_mana" => {
                    $eb = $eb.with(ProvidesMana {
                        mana_amount: effect.1.parse::<i32>().unwrap(),
                    })
                }
                _ => rltk::console::log(format!(
                    "Warning: consumable effect {} not implemented.",
                    effect_name
                )),
            }
        }
    };
}

pub fn spawn_named_item(
    raws: &RawMaster,
    new_entity: EntityBuilder,
    key: &str,
    pos: SpawnType,
) -> Option<Entity> {
    if raws.item_index.contains_key(key) {
        let item_template = &raws.raws.items[raws.item_index[key]];
        let mut eb = spawn_position(pos, new_entity);

        // Renderable
        if let Some(renderable) = &item_template.renderable {
            eb = eb.with(get_renderable_component(renderable));
        }

        eb = eb.with(Name {
            name: item_template.name.clone(),
        });

        eb = eb.with(crate::components::Item {});

        if let Some(stats) = &item_template.stats {
            eb = eb.with(EntityStats {
                power: 0,
                defense: 0,
                pools: HashMap::from([(
                    "hit_points".to_string(),
                    Pool {
                        max: stats.hp,
                        current: stats.hp,
                    },
                )]),
            });
        }

        if let Some(consumable) = &item_template.consumable {
            eb = eb.with(crate::components::Consumable {});
            apply_effects!(consumable.effects, eb);
        }

        return Some(eb.marked::<SimpleMarker<SerializeMe>>().build());
    }
    None
}

pub fn spawn_named_mob(
    raws: &RawMaster,
    new_entity: EntityBuilder,
    key: &str,
    pos: SpawnType,
) -> Option<Entity> {
    if raws.mob_index.contains_key(key) {
        let mob_template = &raws.raws.mobs[raws.mob_index[key]];

        let mut eb = new_entity;

        // Spawn in the specified location
        eb = spawn_position(pos, eb);

        // Renderable
        if let Some(renderable) = &mob_template.renderable {
            eb = eb.with(get_renderable_component(renderable));
        }

        eb = eb
            .with(Name {
                name: mob_template.name.clone(),
            })
            .with(crate::components::Antagonistic {})
            .with(Monster {})
            .with(EntityStats {
                power: mob_template.stats.power,
                defense: mob_template.stats.defense,
                pools: HashMap::from([(
                    "hit_points".to_string(),
                    Pool {
                        max: mob_template.stats.max_hp,
                        current: mob_template.stats.hp,
                    },
                )]),
            })
            .with(Viewshed {
                visible_tiles: Vec::new(),
                range: mob_template.vision_range,
                dirty: true,
            });
        if mob_template.blocks_tile {
            eb = eb.with(BlocksTile {});
        }

        return Some(eb.marked::<SimpleMarker<SerializeMe>>().build());
    }
    None
}

pub fn spawn_named_entity(
    raws: &RawMaster,
    new_entity: EntityBuilder,
    key: &str,
    pos: SpawnType,
) -> Option<Entity> {
    if raws.item_index.contains_key(key) {
        return spawn_named_item(raws, new_entity, key, pos);
    } else if raws.mob_index.contains_key(key) {
        return spawn_named_mob(raws, new_entity, key, pos);
    }

    None
}

pub fn get_spawn_table_for_depth(raws: &RawMaster, depth: i32) -> RandomTable {
    use super::SpawnTableEntry;

    let available_options: Vec<&SpawnTableEntry> = raws
        .raws
        .spawn_table
        .iter()
        .filter(|a| depth >= a.min_depth && depth <= a.max_depth)
        .collect();

    let mut rt = RandomTable::new();
    for e in available_options.iter() {
        let mut weight = e.weight;
        if e.add_map_depth_to_weight.is_some() {
            weight += depth;
        }
        rt = rt.add(e.name.clone(), weight);
    }

    rt
}
