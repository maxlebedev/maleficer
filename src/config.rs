use hocon::HoconLoader;
use serde::Deserialize;
use std::collections::HashMap;
pub use rltk::VirtualKeyCode;



trait FromChar {
    fn from_char (chr: char) -> Self;
}

impl FromChar for VirtualKeyCode{

    fn from_char(chr: char) -> Self{
        //TODO: this is probably the dumbest way to do it
        let key_map: HashMap<char, VirtualKeyCode> = HashMap::from([
            ('a', VirtualKeyCode::A),
            ('b', VirtualKeyCode::B),

            ('d', VirtualKeyCode::D),
            ('g', VirtualKeyCode::G),
            ('i', VirtualKeyCode::I),

            ('j', VirtualKeyCode::J),
            ('k', VirtualKeyCode::K),
            ('l', VirtualKeyCode::L),
            (';', VirtualKeyCode::Semicolon),
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

pub fn cfg_to_kc(val : String ) -> VirtualKeyCode{
    VirtualKeyCode::from_char(val.chars().next().unwrap())
}
