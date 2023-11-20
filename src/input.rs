use std::collections::VecDeque;

use crate::actions::ActorQueue;
use crate::actions::MoveAction;
use crate::board::Position;
use crate::state::GameState;
use crate::Actor;
use crate::Coord;
use crate::Player;
use bevy::input::keyboard::KeyCode;
use bevy::input::keyboard::KeyboardInput;
use bevy::input::ButtonState;
use bevy::prelude::*;

#[derive(Event)]
pub struct PlayerInputReadyEvent;

/*
* KeyboardInput { scan_code: 30, key_code: Some(A) , state: Released, window: 0v0 } }
*/
pub fn read_keyboard_event(
    mut keyboard_input_events: EventReader<KeyboardInput>,
    mut player_query: Query<(Entity, &Position, &mut Actor), With<Player>>,
    mut queue: ResMut<ActorQueue>,
    mut ev_input: EventWriter<PlayerInputReadyEvent>,
) {
    // TODO: read from some input config file
    let key_event = keyboard_input_events.read().next();
    let Ok((entity, position, mut actor)) = player_query.get_single_mut() else {
        return;
    };
    match key_event {
        Some(keyboard_input) => {
            if ButtonState::is_pressed(&keyboard_input.state) {
                let action = match keyboard_input.key_code.unwrap() {
                    KeyCode::Left => MoveAction(entity, position.c + Coord::LEFT),
                    KeyCode::Right => MoveAction(entity, position.c + Coord::RIGHT),
                    KeyCode::Up => MoveAction(entity, position.c + Coord::UP),
                    KeyCode::Down => MoveAction(entity, position.c + Coord::DOWN),
                    _ => MoveAction(entity, position.c), // No move. handle it differently
                                                         // eventually
                };
                actor.0 = Some(Box::new(action));
                queue.0 = VecDeque::from([entity]);
                ev_input.send(PlayerInputReadyEvent);
            }
        }
        _ => (),
    }
}
pub struct InputPlugin;

impl Plugin for InputPlugin {
    fn build(&self, app: &mut App) {
        app.add_systems(
            Update,
            read_keyboard_event.run_if(in_state(GameState::PlayerInput)),
        )
        .add_event::<PlayerInputReadyEvent>();
    }
}
