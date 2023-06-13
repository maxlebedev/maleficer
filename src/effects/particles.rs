use super::*;
use crate::map::Map;
use crate::systems::particle::ParticleBuilder;
use specs::prelude::*;

pub fn particle_to_tile(ecs: &mut World, tile_idx: i32, effect: &EffectSpawner) {
    if let EffectType::Particle {
        glyph,
        fg,
        bg,
        lifespan,
    } = effect.effect_type
    {
        let map = ecs.fetch::<Map>();
        let mut particle_builder = ecs.fetch_mut::<ParticleBuilder>();
        particle_builder.request(
            tile_idx % map.width,
            tile_idx / map.width,
            fg,
            bg,
            glyph,
            lifespan,
        );
    }
}
