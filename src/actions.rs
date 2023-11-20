use crate::board::Position;
use crate::{board::CurrentBoard, Coord};
use crate::{Actor, Player};
use bevy::prelude::*;
use std::collections::VecDeque;

pub trait Action: Send + Sync {
    fn execute(&self, world: &mut World) -> bool;
}

#[derive(Default, Resource)]
pub struct ActorQueue(pub VecDeque<Entity>);

pub struct MoveAction(pub Entity, pub Coord);

impl Action for MoveAction {
    fn execute(&self, world: &mut World) -> bool {
        info!("executing MoveAction");
        let Some(board) = world.get_resource::<CurrentBoard>() else { return false };
        if !board.tiles.contains_key(&self.1) { return false };

        let Some(mut position) = world.get_mut::<Position>(self.0) else { return false };
        position.c = self.1;
        true
    }
}

#[derive(Event)]
pub struct TickEvent;
#[derive(Event)]
pub struct InvalidPlayerActionEvent;
#[derive(Event)]
pub struct ActionsCompleteEvent;
#[derive(Event)]
pub struct NextActorEvent;


pub fn process_action_queue(world: &mut World) {
    let Some(mut queue) = world.get_resource_mut::<ActorQueue>() else { return };
    let Some(entity) = queue.0.pop_front() else {
        world.send_event(ActionsCompleteEvent);
        return;
    };
    let Some(mut actor) = world.get_mut::<Actor>(entity) else { return };
    let Some(action) = actor.0.take() else { return };

    if !action.execute(world) && world.get::<Player>(entity).is_some() {
        world.send_event(InvalidPlayerActionEvent);
        return;
    }
    world.send_event(NextActorEvent);
}

pub struct ActionsPlugin;

impl Plugin for ActionsPlugin {
    fn build(&self, app: &mut App) {
        app.init_resource::<ActorQueue>()
            .add_event::<TickEvent>()
            .add_event::<NextActorEvent>()
            .add_event::<ActionsCompleteEvent>()
            .add_event::<InvalidPlayerActionEvent>()
            .add_systems(Update,
                process_action_queue.run_if(on_event::<TickEvent>())
            );
    }
}
