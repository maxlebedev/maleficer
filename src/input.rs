use crate::board::Position;
use crate::{Coord, GameState};
use bevy::input::keyboard::KeyCode;
use bevy::input::keyboard::KeyboardInput;
use bevy::input::ButtonState;
use bevy::prelude::*;

// TODO: should this be more generic and take an entity to move?
#[derive(Event)]
pub struct PlayerMoveEvent(Coord);

fn apply_move_to_player(
    mut ev_move: EventReader<PlayerMoveEvent>,
    mut next_state: ResMut<NextState<GameState>>,
    mut player_query: Query<&mut Position, With<super::Player>>,
) {
    let Ok(mut position) = player_query.get_single_mut() else {
        return;
    };
    let coord = ev_move.read().next();
    if coord.is_some() {
        position.c += coord.unwrap().0;
        info!("{:?}", coord.unwrap().0);
    }
    next_state.set(GameState::PlayerInput);
}

/*
* KeyboardInput { scan_code: 30, key_code: Some(A) , state: Released, window: 0v0 } }
*/
// TODO: I think we are able to capture multiple events before doing the animations here
pub fn read_keyboard_event(
    mut ev_move: EventWriter<PlayerMoveEvent>,
    mut next_state: ResMut<NextState<GameState>>,
    mut keyboard_input_events: EventReader<KeyboardInput>,
) {
    // TODO: read from some input config file
    let key_event = keyboard_input_events.read().next();
    match key_event {
        Some(keyboard_input) => {
            if ButtonState::is_pressed(&keyboard_input.state) {
                match keyboard_input.key_code.unwrap() {
                    KeyCode::Left => ev_move.send(PlayerMoveEvent(Coord::LEFT)),
                    KeyCode::Right => ev_move.send(PlayerMoveEvent(Coord::RIGHT)),
                    KeyCode::Up => ev_move.send(PlayerMoveEvent(Coord::UP)),
                    KeyCode::Down => ev_move.send(PlayerMoveEvent(Coord::DOWN)),
                    _ => (),
                }
                next_state.set(GameState::TurnResolution);
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
            (
                apply_move_to_player.run_if(in_state(GameState::TurnResolution)),
                read_keyboard_event.run_if(in_state(GameState::PlayerInput)),
            ),
        )
        .add_event::<PlayerMoveEvent>();
    }
}
