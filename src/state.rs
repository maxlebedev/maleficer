use bevy::prelude::*;
//recieve events, change states

#[derive(Clone, Debug, Default, Hash, Eq, States, PartialEq)]
pub enum AppState {
    #[default]
    Menu,
    InGame,
    None
}

#[derive(Clone, Debug, Default, Hash, Eq, States, PartialEq)]
pub enum GameState {
    #[default]
    PlayerInput,
    TurnResolution,
    AITurn,
    AITurnResolution,
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

pub fn animation_stop(
    state: ResMut<State<GameState>>,
    mut next_state: ResMut<NextState<GameState>>,
) {
    match state.get(){
        GameState::TurnResolution => next_state.set(GameState::AITurn),
        GameState::AITurnResolution => next_state.set(GameState::PlayerInput),
        _ => ()
    };
}

#[derive(Event)]
pub struct NextStateEvent;

#[derive(Event)]
pub struct AnimationStopEvent;

pub fn turn_loop(
    state: ResMut<State<GameState>>,
    mut next_state: ResMut<NextState<GameState>>,
) {
    let next = match state.get(){
        GameState::PlayerInput => GameState::TurnResolution,
        GameState::TurnResolution => GameState::AITurn,
        GameState::AITurn => GameState::AITurnResolution,
        GameState::AITurnResolution => GameState::PlayerInput,
    };
    info!("new state: {:?}", next);
    next_state.set(next);
}


pub struct StatePlugin;

impl Plugin for StatePlugin {
    fn build(&self, app: &mut App) {
        app.add_state::<AppState>()
            .add_state::<GameState>()
            .add_event::<NextStateEvent>()
            .add_event::<AnimationStopEvent>()
            .add_event::<ChangeStateEvent>()
            .add_systems(
                Update,
                change_state_via_event.run_if(in_state(AppState::InGame)),
            )
            .add_systems(
                Update,
                turn_loop.run_if(on_event::<NextStateEvent>()),
            )
            .add_systems(
                Update,
                animation_stop.run_if(on_event::<AnimationStopEvent>()),
            )
        ;
    }
}


use crate::actions::{TickEvent, ActionsCompleteEvent, InvalidPlayerActionEvent};
use crate::graphics::GraphicsWaitEvent;
use crate::input::PlayerInputReadyEvent;

fn game_start(
    mut next_state: ResMut<NextState<GameState>>
) {
    info!("game start");
    next_state.set(GameState::PlayerInput);
}

fn game_end(
    mut next_state: ResMut<NextState<AppState>>
) {
    next_state.set(AppState::None);
}

fn turn_update_start(
    mut next_state: ResMut<NextState<GameState>>,
    mut ev_tick: EventWriter<TickEvent>
) {
    next_state.set(GameState::TurnResolution);
    ev_tick.send(TickEvent);
}

fn tick(
    mut ev_wait: EventReader<GraphicsWaitEvent>,
    mut ev_tick: EventWriter<TickEvent>
) {
    if ev_wait.read().len() == 0 {
        ev_tick.send(TickEvent);
    }
}

fn turn_update_end(
    mut next_state: ResMut<NextState<GameState>>
) {
    next_state.set(GameState::PlayerInput);
}

fn turn_update_cancel(
    mut next_state: ResMut<NextState<GameState>>
) {
    next_state.set(GameState::PlayerInput);
}

pub struct ManagerPlugin;

impl Plugin for ManagerPlugin {
    fn build(&self, app: &mut App) {
        info!("manager plugin");
        app.add_systems(OnEnter(AppState::InGame), game_start)
            .add_systems(OnExit(AppState::InGame), game_end)
            .add_systems(Update, turn_update_start.run_if(on_event::<PlayerInputReadyEvent>()))
            .add_systems(Update, turn_update_end.run_if(on_event::<ActionsCompleteEvent>()))
            .add_systems(Update, turn_update_cancel.run_if(on_event::<InvalidPlayerActionEvent>()))
            .add_systems(Update, tick.run_if(in_state(GameState::TurnResolution)));
    }
}
