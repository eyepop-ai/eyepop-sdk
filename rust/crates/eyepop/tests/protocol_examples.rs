use eyepop::protocol::{Command, Message};
use serde_json::Value;
use std::fs;

const EXAMPLES: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/../../../protocol/examples");

enum Raw {
    Number(String),
    Array(Vec<Raw>),
    Object(Vec<(String, Raw)>),
    Leaf(Value),
}

fn skip_space(bytes: &[u8], at: &mut usize) {
    while *at < bytes.len() && bytes[*at].is_ascii_whitespace() {
        *at += 1;
    }
}

fn parse_raw(text: &str, at: &mut usize) -> Raw {
    let bytes = text.as_bytes();
    skip_space(bytes, at);
    let start = *at;
    match bytes[start] {
        b'[' | b'{' => {
            *at += 1;
            let mut items = Vec::new();
            loop {
                skip_space(bytes, at);
                match bytes[*at] {
                    b']' | b'}' => break *at += 1,
                    b',' => *at += 1,
                    _ if bytes[start] == b'{' => {
                        let Raw::Leaf(Value::String(key)) = parse_raw(text, at) else {
                            panic!("object key is not a string");
                        };
                        skip_space(bytes, at);
                        *at += 1;
                        items.push((key, parse_raw(text, at)));
                    }
                    _ => items.push((String::new(), parse_raw(text, at))),
                }
            }
            if bytes[start] == b'{' {
                Raw::Object(items)
            } else {
                Raw::Array(items.into_iter().map(|(_, item)| item).collect())
            }
        }
        b'"' => {
            *at += 1;
            while bytes[*at] != b'"' {
                *at += if bytes[*at] == b'\\' { 2 } else { 1 };
            }
            *at += 1;
            Raw::Leaf(serde_json::from_str(&text[start..*at]).unwrap())
        }
        b'-' | b'0'..=b'9' => {
            while *at < bytes.len()
                && matches!(bytes[*at], b'-' | b'+' | b'.' | b'e' | b'E' | b'0'..=b'9')
            {
                *at += 1;
            }
            Raw::Number(text[start..*at].to_string())
        }
        _ => {
            while *at < bytes.len() && bytes[*at].is_ascii_alphabetic() {
                *at += 1;
            }
            Raw::Leaf(serde_json::from_str(&text[start..*at]).unwrap())
        }
    }
}

fn canonical(token: &str) -> String {
    let (mantissa, exponent) = token.split_once(['e', 'E']).unwrap_or((token, "0"));
    let mut exponent: i64 = exponent.parse().unwrap();
    let (sign, mantissa) = mantissa
        .strip_prefix('-')
        .map_or(("", mantissa), |m| ("-", m));
    let (whole, fraction) = mantissa.split_once('.').unwrap_or((mantissa, ""));
    let digits = format!("{whole}{fraction}");
    let digits = digits.trim_start_matches('0');
    if digits.is_empty() {
        return "0".to_string();
    }
    let significant = digits.trim_end_matches('0');
    exponent += (digits.len() - significant.len()) as i64 - fraction.len() as i64;
    format!("{sign}{significant}e{exponent}")
}

fn same(a: &Value, b: &Raw) -> bool {
    match (a, b) {
        (Value::Number(x), Raw::Number(y)) => canonical(&x.to_string()) == canonical(y),
        (Value::Array(x), Raw::Array(y)) => {
            x.len() == y.len() && x.iter().zip(y).all(|(a, b)| same(a, b))
        }
        (Value::Object(x), Raw::Object(y)) => {
            x.len() == y.len()
                && y.iter()
                    .all(|(key, b)| x.get(key).is_some_and(|a| same(a, b)))
        }
        (a, Raw::Leaf(b)) => a == b,
        _ => false,
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
    if same(&encoded, &parse_raw(text, &mut 0)) != case["unchanged"].as_bool().unwrap() {
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
