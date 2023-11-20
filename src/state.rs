use bevy::prelude::*;

#[derive(Clone, Debug, Default, Hash, Eq, States, PartialEq)]
pub enum AppState {
    #[default]
    Menu,
    InGame,
    None,
}

#[derive(Clone, Debug, Default, Hash, Eq, States, PartialEq)]
pub enum GameState {
    #[default]
    PlayerInput,
    TurnResolution,
    AITurn,
    AITurnResolution,
}

pub struct StatePlugin;

impl Plugin for StatePlugin {
    fn build(&self, app: &mut App) {
        app.add_state::<AppState>().add_state::<GameState>();
    }
}

use crate::actions::{ActionsCompleteEvent, InvalidPlayerActionEvent, TickEvent};
use crate::graphics::GraphicsWaitEvent;
use crate::input::PlayerInputReadyEvent;

fn game_start(mut next_state: ResMut<NextState<GameState>>) {
    info!("game start");
    next_state.set(GameState::PlayerInput);
}

fn game_end(mut next_state: ResMut<NextState<AppState>>) {
    next_state.set(AppState::None);
}

fn turn_update_start(
    mut next_state: ResMut<NextState<GameState>>,
    mut ev_tick: EventWriter<TickEvent>,
) {
    next_state.set(GameState::TurnResolution);
    ev_tick.send(TickEvent);
}

fn tick(mut ev_wait: EventReader<GraphicsWaitEvent>, mut ev_tick: EventWriter<TickEvent>) {
    if ev_wait.read().len() == 0 {
        ev_tick.send(TickEvent);
    }
}

fn turn_update_end(mut next_state: ResMut<NextState<GameState>>) {
    next_state.set(GameState::PlayerInput);
}

fn turn_update_cancel(mut next_state: ResMut<NextState<GameState>>) {
    next_state.set(GameState::PlayerInput);
}

pub struct ManagerPlugin;

impl Plugin for ManagerPlugin {
    fn build(&self, app: &mut App) {
        info!("manager plugin");
        app.add_systems(OnEnter(AppState::InGame), game_start)
            .add_systems(OnExit(AppState::InGame), game_end)
            .add_systems(
                Update,
                turn_update_start.run_if(on_event::<PlayerInputReadyEvent>()),
            )
            .add_systems(
                Update,
                turn_update_end.run_if(on_event::<ActionsCompleteEvent>()),
            )
            .add_systems(
                Update,
                turn_update_cancel.run_if(on_event::<InvalidPlayerActionEvent>()),
            )
            .add_systems(Update, tick.run_if(in_state(GameState::TurnResolution)));
    }
}
