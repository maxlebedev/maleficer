use bevy::prelude::*;
//recieve events, change states

#[derive(Clone, Debug, Default, Hash, Eq, States, PartialEq)]
pub enum AppState {
    #[default]
    Menu,
    InGame,
}

#[derive(Clone, Debug, Default, Hash, Eq, States, PartialEq)]
pub enum GameState {
    #[default]
    PlayerInput,
    TurnResolution,
    //AITurn,
}

#[derive(Event)]
pub struct ChangeStateEvent(pub GameState);

/// This might be a useless bit of indirection. tbd
pub fn change_state_via_event(
    mut ev_state: EventReader<ChangeStateEvent>,
    mut next_state: ResMut<NextState<GameState>>,
) {
    let new_state = ev_state.read().next();
    if new_state.is_none() {
        return;
    }
    next_state.set(new_state.unwrap().0.clone());
}

pub struct StatePlugin;

impl Plugin for StatePlugin {
    fn build(&self, app: &mut App) {
        app.add_state::<AppState>()
            .add_state::<GameState>()
            .add_event::<ChangeStateEvent>()
            .add_systems(
                Update,
                change_state_via_event.run_if(in_state(AppState::InGame)),
            );
    }
}
