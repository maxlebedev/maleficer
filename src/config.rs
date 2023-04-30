use hocon::HoconLoader;
pub use rltk::VirtualKeyCode;
use serde::Deserialize;
use std::collections::HashMap;

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
            ("a", VirtualKeyCode::A),
            ("b", VirtualKeyCode::B),
            ("d", VirtualKeyCode::D),
            ("g", VirtualKeyCode::G),
            ("i", VirtualKeyCode::I),
            ("j", VirtualKeyCode::J),
            ("k", VirtualKeyCode::K),
            ("l", VirtualKeyCode::L),
            (";", VirtualKeyCode::Semicolon),
            ("escape", VirtualKeyCode::Escape),
            ("return", VirtualKeyCode::Return),
            ("space", VirtualKeyCode::Space),
            ("w", VirtualKeyCode::W),
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
    pub inventory: String,
    pub drop: String,
    pub exit: String,
    pub select: String,
    pub wait: String,
    pub hk1: String,

    pub width: i32,
    pub height: i32,
}

lazy_static! {
    pub static ref CONFIG: Config = get_config();
}

fn get_config() -> Config {
    let configs: Config = HoconLoader::new()
        .load_file("./keybinds.conf")
        .expect("Config load err")
        .resolve()
        .expect("Config deserialize err");
    configs
}

pub fn cfg_to_kc(val: &str) -> VirtualKeyCode {
    VirtualKeyCode::from_str(val)
}
