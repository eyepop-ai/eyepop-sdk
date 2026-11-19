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

#[test]
fn decoding_cases_are_known_or_unknown_and_keep_exact_numbers() {
    let path = concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../../protocol/examples/decoding.json"
    );
    let cases: Vec<Value> = serde_json::from_str(&fs::read_to_string(path).unwrap()).unwrap();
    for case in cases {
        let name = case["name"].as_str().unwrap();
        let data: Value = serde_json::from_str(case["text"].as_str().unwrap()).unwrap();
        let (known, encoded) = if case["union"] == "command" {
            let command = Command::decode(&data);
            (!matches!(command, Command::Unknown(_)), command.to_json())
        } else {
            let message = Message::decode(&data);
            (!matches!(message, Message::Unknown(_)), message.to_json())
        };
        assert_eq!(known, case["known"].as_bool().unwrap(), "{name}");
        if let Some(keeps) = case.get("keeps") {
            assert!(
                encoded.to_string().contains(keeps.as_str().unwrap()),
                "{name}: {encoded}"
            );
        }
    }
}

#[test]
fn a_field_set_to_none_is_removed_from_the_retained_json() {
    let data: Value = serde_json::from_str(r#"{"type":"setSource","id":"s1","url":"u"}"#).unwrap();
    let Command::SetSource(mut source) = Command::decode(&data) else {
        panic!("not a setSource");
    };
    source.url = None;
    source.assetUuid = Some("a".to_string());

    let expected: Value =
        serde_json::from_str(r#"{"type":"setSource","id":"s1","assetUuid":"a"}"#).unwrap();
    assert_eq!(Command::SetSource(source).to_json(), expected);
}
