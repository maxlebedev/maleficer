use hocon::HoconLoader;
pub use rltk::VirtualKeyCode;
use serde::Deserialize;
use std::collections::HashMap;

use crate::gui;

trait FromStr {
    fn from_str(chr: &str) -> Self;
}

impl FromStr for VirtualKeyCode {
    fn from_str(chr: &str) -> Self {
        //TODO: this is probably the dumbest way to do it
        //I hope this doesn't get instantiated every time we use from_str
        let key_map: HashMap<&str, VirtualKeyCode> = HashMap::from([
            ("1", VirtualKeyCode::Key1),
            ("2", VirtualKeyCode::Key2),
            ("3", VirtualKeyCode::Key3),
            ("4", VirtualKeyCode::Key4),
            ("5", VirtualKeyCode::Key5),
            ("6", VirtualKeyCode::Key6),
            ("7", VirtualKeyCode::Key7),
            ("8", VirtualKeyCode::Key8),
            ("9", VirtualKeyCode::Key9),
            ("0", VirtualKeyCode::Key0),
            ("-", VirtualKeyCode::Minus),
            ("+", VirtualKeyCode::Plus),
            ("a", VirtualKeyCode::A),
            ("b", VirtualKeyCode::B),
            ("c", VirtualKeyCode::C),
            ("d", VirtualKeyCode::D),
            ("e", VirtualKeyCode::E),
            ("f", VirtualKeyCode::F),
            ("g", VirtualKeyCode::G),
            ("h", VirtualKeyCode::H),
            ("i", VirtualKeyCode::I),
            ("j", VirtualKeyCode::J),
            ("k", VirtualKeyCode::K),
            ("l", VirtualKeyCode::L),
            ("m", VirtualKeyCode::M),
            ("n", VirtualKeyCode::N),
            ("o", VirtualKeyCode::O),
            ("p", VirtualKeyCode::P),
            ("q", VirtualKeyCode::Q),
            ("r", VirtualKeyCode::R),
            ("s", VirtualKeyCode::S),
            ("t", VirtualKeyCode::T),
            ("u", VirtualKeyCode::U),
            ("v", VirtualKeyCode::V),
            ("w", VirtualKeyCode::W),
            ("x", VirtualKeyCode::X),
            ("y", VirtualKeyCode::Y),
            ("z", VirtualKeyCode::Z),
            ("escape", VirtualKeyCode::Escape),
            ("return", VirtualKeyCode::Return),
            ("space", VirtualKeyCode::Space),
            ("left", VirtualKeyCode::Left),
            ("down", VirtualKeyCode::Down),
            ("right", VirtualKeyCode::Right),
            ("up", VirtualKeyCode::Up),
            ("back", VirtualKeyCode::Back),
            ("shift", VirtualKeyCode::LShift),
            ("alt", VirtualKeyCode::LAlt),
            ("ctrl", VirtualKeyCode::LControl),
            ("tab", VirtualKeyCode::Tab),
            ("/", VirtualKeyCode::Slash),
            (";", VirtualKeyCode::Semicolon),
            (":", VirtualKeyCode::Colon),
            (",", VirtualKeyCode::Comma),
            (".", VirtualKeyCode::Period),
        ]);
        *key_map.get(&chr).unwrap()
    }
}

#[derive(Deserialize, Debug)]
pub struct Config {
    pub left: String,
    pub down: String,
    pub up: String,
    pub right: String,
    pub pick_up: String,
    pub exit: String,
    pub select: String,
    pub wait: String,
    pub hk1: String,
    pub hk2: String,
    pub hk3: String,
    pub hk4: String,
    pub hk5: String,
    pub hk6: String,
    pub hk7: String,
    pub hk8: String,
    pub hk9: String,
    pub hk10: String,
}

pub struct Input {
    pub left: VirtualKeyCode,
    pub down: VirtualKeyCode,
    pub up: VirtualKeyCode,
    pub right: VirtualKeyCode,
    pub pick_up: VirtualKeyCode,
    pub exit: VirtualKeyCode,
    pub select: VirtualKeyCode,
    pub wait: VirtualKeyCode,
    pub hk1: VirtualKeyCode,
    pub hk2: VirtualKeyCode,
    pub hk3: VirtualKeyCode,
    pub hk4: VirtualKeyCode,
    pub hk5: VirtualKeyCode,
    pub hk6: VirtualKeyCode,
    pub hk7: VirtualKeyCode,
    pub hk8: VirtualKeyCode,
    pub hk9: VirtualKeyCode,
    pub hk10: VirtualKeyCode,
}

lazy_static! {
    pub static ref CONFIG: Config = get_config();
    pub static ref INPUT: Input = Input {
        left: VirtualKeyCode::from_str(CONFIG.left.as_str()),
        down: VirtualKeyCode::from_str(CONFIG.down.as_str()),
        up: VirtualKeyCode::from_str(CONFIG.up.as_str()),
        right: VirtualKeyCode::from_str(CONFIG.right.as_str()),
        pick_up: VirtualKeyCode::from_str(CONFIG.pick_up.as_str()),
        exit: VirtualKeyCode::from_str(CONFIG.exit.as_str()),
        select: VirtualKeyCode::from_str(CONFIG.select.as_str()),
        wait: VirtualKeyCode::from_str(CONFIG.wait.as_str()),
        hk1: VirtualKeyCode::from_str(CONFIG.hk1.as_str()),
        hk2: VirtualKeyCode::from_str(CONFIG.hk2.as_str()),
        hk3: VirtualKeyCode::from_str(CONFIG.hk3.as_str()),
        hk4: VirtualKeyCode::from_str(CONFIG.hk4.as_str()),
        hk5: VirtualKeyCode::from_str(CONFIG.hk5.as_str()),
        hk6: VirtualKeyCode::from_str(CONFIG.hk6.as_str()),
        hk7: VirtualKeyCode::from_str(CONFIG.hk7.as_str()),
        hk8: VirtualKeyCode::from_str(CONFIG.hk8.as_str()),
        hk9: VirtualKeyCode::from_str(CONFIG.hk9.as_str()),
        hk10: VirtualKeyCode::from_str(CONFIG.hk10.as_str()),
    };
}

#[derive(Deserialize, Debug)]
pub struct Bounds {
    pub win_width: usize,
    pub win_height: usize,
    // pub map_width: usize,
    // pub map_height: usize,
    pub view_width: usize,
    pub view_height: usize,
}

pub const BOUNDS: Bounds = Bounds {
    win_width: 120, // this is 1920x1080 for now
    win_height: 62,
    // map_width: 100, // these are better stored in map.width
    // map_height: 100, // and map.height
    view_width: 120 - gui::UI_WIDTH - gui::UI_WIDTH,
    view_height: 62,
};

fn get_config() -> Config {
    let configs: Config = HoconLoader::new()
        .load_file("./keybinds.conf")
        .expect("Config load err")
        .resolve()
        .expect("Config deserialize err");
    configs
}
