use eyepop::protocol::{Command, Message};
use serde_json::Value;
use std::fs;

fn same(a: &Value, b: &Value) -> bool {
    match (a, b) {
        (Value::Number(x), Value::Number(y)) => x.as_f64() == y.as_f64(),
        (Value::Array(x), Value::Array(y)) => {
            x.len() == y.len() && x.iter().zip(y).all(|(a, b)| same(a, b))
        }
        (Value::Object(x), Value::Object(y)) => {
            x.len() == y.len()
                && x.iter()
                    .all(|(key, a)| y.get(key).is_some_and(|b| same(a, b)))
        }
        _ => a == b,
    }
}

#[test]
fn every_valid_example_decodes_to_a_known_variant_and_encodes_back_unchanged() {
    let dir = concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../../protocol/examples/valid"
    );
    let mut seen = 0;
    for entry in fs::read_dir(dir).unwrap() {
        let path = entry.unwrap().path();
        let name = path.file_name().unwrap().to_str().unwrap().to_string();
        let data: Value = serde_json::from_str(&fs::read_to_string(&path).unwrap()).unwrap();
        let encoded = if name.starts_with("command-") {
            let command = Command::decode(&data);
            assert!(
                !matches!(command, Command::Unknown(_)),
                "{name} decoded to Unknown"
            );
            command.to_json()
        } else {
            let message = Message::decode(&data);
            assert!(
                !matches!(message, Message::Unknown(_)),
                "{name} decoded to Unknown"
            );
            message.to_json()
        };
        assert!(same(&encoded, &data), "{name}: {encoded} != {data}");
        seen += 1;
    }
    assert!(seen > 30);
}
