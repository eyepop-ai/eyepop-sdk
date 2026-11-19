use eyepop::protocol::{Command, Message};
use serde_json::{Number, Value};
use std::fs;

const EXAMPLES: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/../../../protocol/examples");

fn integer(n: &Number) -> Option<i128> {
    n.as_i64()
        .map(i128::from)
        .or_else(|| n.as_u64().map(i128::from))
        .or_else(|| {
            n.as_f64()
                .filter(|f| f.fract() == 0.0 && f.abs() < 2f64.powi(127))
                .map(|f| f as i128)
        })
}

fn same(a: &Value, b: &Value) -> bool {
    match (a, b) {
        (Value::Number(x), Value::Number(y)) => match (integer(x), integer(y)) {
            (Some(x), Some(y)) => x == y,
            (None, None) => x.as_f64() == y.as_f64(),
            _ => false,
        },
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

fn problem(case: &Value, text: &str) -> Option<String> {
    let data: Value = match serde_json::from_str(text) {
        Ok(data) => data,
        Err(error) => return Some(error.to_string()),
    };
    let (unknown, encoded) = if case["union"] == "command" {
        let command = Command::decode(&data);
        (matches!(command, Command::Unknown(_)), command.to_json())
    } else {
        let message = Message::decode(&data);
        (matches!(message, Message::Unknown(_)), message.to_json())
    };
    let variant = if unknown {
        "Unknown"
    } else {
        encoded["type"].as_str().unwrap()
    };
    if case["variant"] != variant {
        return Some(format!("decoded to {variant}, want {}", case["variant"]));
    }
    if same(&encoded, &data) != case["unchanged"].as_bool().unwrap() {
        return Some(format!(
            "encoded {encoded}, want unchanged = {}",
            case["unchanged"]
        ));
    }
    if let Some(keeps) = case["keeps"].as_str() {
        if !encoded.to_string().contains(keeps) {
            return Some(format!("encoded {encoded}, want it to contain {keeps}"));
        }
    }
    None
}

#[test]
fn every_decoding_case_has_its_stated_outcome() {
    let cases: Vec<Value> =
        serde_json::from_str(&fs::read_to_string(format!("{EXAMPLES}/decoding.json")).unwrap())
            .unwrap();
    assert!(cases.len() > 60);
    let mut failures = Vec::new();
    for case in &cases {
        let (name, text) = match case["file"].as_str() {
            Some(file) => (
                file,
                fs::read_to_string(format!("{EXAMPLES}/{file}")).unwrap(),
            ),
            None => (
                case["name"].as_str().unwrap(),
                case["text"].as_str().unwrap().to_string(),
            ),
        };
        match (case["diverges"].get("rust"), problem(case, &text)) {
            (Some(reason), None) => failures.push(format!(
                "{name}: passes but is marked as a known Rust divergence ({reason}); remove the marker"
            )),
            (None, Some(problem)) => failures.push(format!("{name}: {problem}")),
            _ => {}
        }
    }
    assert!(failures.is_empty(), "{}", failures.join("\n"));
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
