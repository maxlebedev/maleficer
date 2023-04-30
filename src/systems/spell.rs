use crate::{gamelog::GameLog, InflictsDamage, Name, Ranged, SerializeMe, Spell, WantsToCastSpell};

use specs::saveload::MarkedBuilder;
use specs::{prelude::*, saveload::SimpleMarker};
// Spells look a lot like items, key difference is they are not consumable, and don't interact with
// the inventory

pub struct SpellCast {}

impl<'a> System<'a> for SpellCast {
    type SystemData = (
        ReadExpect<'a, Entity>,
        WriteExpect<'a, GameLog>,
        WriteStorage<'a, WantsToCastSpell>,
    );

    fn run(&mut self, data: Self::SystemData) {
        // for now, if its the player casting, we just log something
        let (player_entity, mut gamelog, mut wants_spellcast) = data;

        for cast in wants_spellcast.join() {
            if cast.source == *player_entity {
                gamelog.entries.push(format!("You cast a spell"));
            }
        }
        wants_spellcast.clear();
    }
}

pub fn fireball_spell(ecs: &mut World, hkey: String) {
    ecs.create_entity()
        .with(Name {
            name: "Fireball Spell".to_string(),
        })
        .with(Spell { hotkey: hkey })
        .with(Ranged { range: 6 })
        .with(InflictsDamage { damage: 8 })
        .marked::<SimpleMarker<SerializeMe>>()
        .build();
}
