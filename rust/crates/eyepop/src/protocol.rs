// Generated from protocol/schema by protocol/scripts/generate.py. Do not edit.
#![allow(dead_code, non_snake_case, clippy::all)]

use serde_json::{Map, Value};

#[derive(Debug, Clone, PartialEq)]
pub struct DecodeError(pub String);

fn fail<T>(message: String) -> std::result::Result<T, DecodeError> {
    Err(DecodeError(message))
}

fn parse_object(value: &Value) -> std::result::Result<&Map<String, Value>, DecodeError> {
    match value {
        Value::Object(map) => Ok(map),
        _ => fail(format!("expected an object, got {value}")),
    }
}

fn parse_string(value: &Value) -> std::result::Result<String, DecodeError> {
    match value {
        Value::String(text) => Ok(text.clone()),
        _ => fail(format!("expected a string, got {value}")),
    }
}

fn parse_integer(value: &Value) -> std::result::Result<i64, DecodeError> {
    let whole = match value {
        Value::Number(number) => number
            .as_i64()
            .map(i128::from)
            .or_else(|| number.as_u64().map(i128::from))
            .or_else(|| number.as_f64().filter(|f| f.is_finite() && f.fract() == 0.0).map(|f| f as i128)),
        _ => None,
    };
    match whole {
        Some(whole) if (INTEGER_MINIMUM..=INTEGER_MAXIMUM).contains(&whole) => Ok(whole as i64),
        _ => fail(format!("expected an integer from {INTEGER_MINIMUM} to {INTEGER_MAXIMUM}, got {value}")),
    }
}

fn parse_number(value: &Value) -> std::result::Result<f64, DecodeError> {
    match value.as_f64() {
        Some(number) if number.is_finite() => Ok(number),
        _ => fail(format!("expected a finite number, got {value}")),
    }
}

fn parse_boolean(value: &Value) -> std::result::Result<bool, DecodeError> {
    match value {
        Value::Bool(flag) => Ok(*flag),
        _ => fail(format!("expected a boolean, got {value}")),
    }
}

fn limit<T>(
    parse: impl Fn(&Value) -> std::result::Result<T, DecodeError>,
    measure: impl Fn(&T) -> f64,
    minimum: Option<f64>,
    exclusive_minimum: Option<f64>,
    exclusive_maximum: Option<f64>,
) -> impl Fn(&Value) -> std::result::Result<T, DecodeError> {
    move |value| {
        let parsed = parse(value)?;
        let size = measure(&parsed);
        if minimum.is_some_and(|bound| size < bound)
            || exclusive_minimum.is_some_and(|bound| size <= bound)
            || exclusive_maximum.is_some_and(|bound| size >= bound)
        {
            return fail(format!("{value} is out of range"));
        }
        Ok(parsed)
    }
}

fn exactly_one(obj: &Map<String, Value>, keys: &[&str]) -> std::result::Result<(), DecodeError> {
    let present = keys.iter().filter(|key| obj.contains_key(**key)).count();
    if present == 1 {
        Ok(())
    } else {
        fail(format!("expected exactly one of {keys:?}, got {present}"))
    }
}

fn within(value: &Value, levels: usize) -> bool {
    match value {
        Value::Object(map) => levels > 0 && map.values().all(|item| within(item, levels - 1)),
        Value::Array(items) => levels > 0 && items.iter().all(|item| within(item, levels - 1)),
        _ => true,
    }
}

fn put_number(out: &mut Map<String, Value>, key: &str, number: f64) {
    if out.get(key).and_then(Value::as_f64) != Some(number) {
        out.insert(key.to_string(), number_to_json(number));
    }
}

fn parse_free(value: &Value) -> std::result::Result<Map<String, Value>, DecodeError> {
    parse_object(value).cloned()
}

fn parse_const(expected: &'static str) -> impl Fn(&Value) -> std::result::Result<(), DecodeError> {
    move |value| match value {
        Value::String(text) if text == expected => Ok(()),
        _ => fail(format!("expected {expected:?}, got {value}")),
    }
}

fn parse_array<T>(
    item: impl Fn(&Value) -> std::result::Result<T, DecodeError>,
) -> impl Fn(&Value) -> std::result::Result<Vec<T>, DecodeError> {
    move |value| match value {
        Value::Array(elements) => elements.iter().map(&item).collect(),
        _ => fail(format!("expected an array, got {value}")),
    }
}

fn required<T>(
    obj: &Map<String, Value>,
    key: &str,
    parse: impl Fn(&Value) -> std::result::Result<T, DecodeError>,
) -> std::result::Result<T, DecodeError> {
    match obj.get(key) {
        Some(value) => parse(value),
        None => fail(format!("missing {key}")),
    }
}

fn optional<T>(
    obj: &Map<String, Value>,
    key: &str,
    parse: impl Fn(&Value) -> std::result::Result<T, DecodeError>,
) -> std::result::Result<Option<T>, DecodeError> {
    obj.get(key).map(parse).transpose()
}

fn number_to_json(number: f64) -> Value {
    if number.fract() == 0.0 && number.abs() < 9.0e15 {
        Value::from(number as i64)
    } else {
        Value::from(number)
    }
}

const INTEGER_MINIMUM: i128 = -9223372036854775808;
const INTEGER_MAXIMUM: i128 = 9223372036854775807;
const MAX_DEPTH: usize = 64;

pub(crate) fn length(text: &String) -> f64 {
    text.chars().count() as f64
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum EndReason {
    Eos,
    Error,
    Preempted,
    Stopped,
}

impl EndReason {
    pub fn from_json(value: &Value) -> std::result::Result<EndReason, DecodeError> {
        match value.as_str() {
            Some("eos") => Ok(EndReason::Eos),
            Some("error") => Ok(EndReason::Error),
            Some("preempted") => Ok(EndReason::Preempted),
            Some("stopped") => Ok(EndReason::Stopped),
            _ => fail(format!("unexpected value {value}")),
        }
    }

    pub fn to_json(&self) -> Value {
        match self {
            EndReason::Eos => Value::from("eos"),
            EndReason::Error => Value::from("error"),
            EndReason::Preempted => Value::from("preempted"),
            EndReason::Stopped => Value::from("stopped"),
        }
    }
}


#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GetGraphFormat {
    Dot,
    Png,
    Pdf,
}

impl GetGraphFormat {
    pub fn from_json(value: &Value) -> std::result::Result<GetGraphFormat, DecodeError> {
        match value.as_str() {
            Some("dot") => Ok(GetGraphFormat::Dot),
            Some("png") => Ok(GetGraphFormat::Png),
            Some("pdf") => Ok(GetGraphFormat::Pdf),
            _ => fail(format!("unexpected value {value}")),
        }
    }

    pub fn to_json(&self) -> Value {
        match self {
            GetGraphFormat::Dot => Value::from("dot"),
            GetGraphFormat::Png => Value::from("png"),
            GetGraphFormat::Pdf => Value::from("pdf"),
        }
    }
}


#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SetSourceMode {
    Queue,
    Preempt,
}

impl SetSourceMode {
    pub fn from_json(value: &Value) -> std::result::Result<SetSourceMode, DecodeError> {
        match value.as_str() {
            Some("queue") => Ok(SetSourceMode::Queue),
            Some("preempt") => Ok(SetSourceMode::Preempt),
            _ => fail(format!("unexpected value {value}")),
        }
    }

    pub fn to_json(&self) -> Value {
        match self {
            SetSourceMode::Queue => Value::from("queue"),
            SetSourceMode::Preempt => Value::from("preempt"),
        }
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct Ability {
    pub ability: Option<String>,
    pub abilityUuid: Option<String>,
    pub params: Option<Map<String, Value>>,
    pub raw: Map<String, Value>,
}

impl Ability {
    pub fn from_json(value: &Value) -> std::result::Result<Ability, DecodeError> {
        let obj = parse_object(value)?;
        exactly_one(obj, &["ability", "abilityUuid"])?;
        Ok(Ability {
            ability: optional(obj, "ability", parse_string)?,
            abilityUuid: optional(obj, "abilityUuid", parse_string)?,
            params: optional(obj, "params", parse_free)?,
            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        if let Some(x) = &self.ability {
            out.insert("ability".to_string(), Value::String(x.clone()));
        } else {
            out.remove("ability");
        }
        if let Some(x) = &self.abilityUuid {
            out.insert("abilityUuid".to_string(), Value::String(x.clone()));
        } else {
            out.remove("abilityUuid");
        }
        if let Some(x) = &self.params {
            out.insert("params".to_string(), Value::Object(x.clone()));
        } else {
            out.remove("params");
        }
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct CameraIntrinsics {
    pub fx: f64,
    pub fy: f64,
    pub cx: f64,
    pub cy: f64,
    pub raw: Map<String, Value>,
}

impl CameraIntrinsics {
    pub fn from_json(value: &Value) -> std::result::Result<CameraIntrinsics, DecodeError> {
        let obj = parse_object(value)?;
        Ok(CameraIntrinsics {
            fx: required(obj, "fx", parse_number)?,
            fy: required(obj, "fy", parse_number)?,
            cx: required(obj, "cx", parse_number)?,
            cy: required(obj, "cy", parse_number)?,
            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        put_number(&mut out, "fx", self.fx);
        put_number(&mut out, "fy", self.fy);
        put_number(&mut out, "cx", self.cx);
        put_number(&mut out, "cy", self.cy);
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct CameraDistortion {
    pub k1: Option<f64>,
    pub k2: Option<f64>,
    pub p1: Option<f64>,
    pub p2: Option<f64>,
    pub k3: Option<f64>,
    pub raw: Map<String, Value>,
}

impl CameraDistortion {
    pub fn from_json(value: &Value) -> std::result::Result<CameraDistortion, DecodeError> {
        let obj = parse_object(value)?;
        Ok(CameraDistortion {
            k1: optional(obj, "k1", parse_number)?,
            k2: optional(obj, "k2", parse_number)?,
            p1: optional(obj, "p1", parse_number)?,
            p2: optional(obj, "p2", parse_number)?,
            k3: optional(obj, "k3", parse_number)?,
            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        if let Some(x) = &self.k1 {
            put_number(&mut out, "k1", *x);
        } else {
            out.remove("k1");
        }
        if let Some(x) = &self.k2 {
            put_number(&mut out, "k2", *x);
        } else {
            out.remove("k2");
        }
        if let Some(x) = &self.p1 {
            put_number(&mut out, "p1", *x);
        } else {
            out.remove("p1");
        }
        if let Some(x) = &self.p2 {
            put_number(&mut out, "p2", *x);
        } else {
            out.remove("p2");
        }
        if let Some(x) = &self.k3 {
            put_number(&mut out, "k3", *x);
        } else {
            out.remove("k3");
        }
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct CameraExtrinsicsRotation {
    pub w: f64,
    pub x: f64,
    pub y: f64,
    pub z: f64,
    pub raw: Map<String, Value>,
}

impl CameraExtrinsicsRotation {
    pub fn from_json(value: &Value) -> std::result::Result<CameraExtrinsicsRotation, DecodeError> {
        let obj = parse_object(value)?;
        Ok(CameraExtrinsicsRotation {
            w: required(obj, "w", parse_number)?,
            x: required(obj, "x", parse_number)?,
            y: required(obj, "y", parse_number)?,
            z: required(obj, "z", parse_number)?,
            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        put_number(&mut out, "w", self.w);
        put_number(&mut out, "x", self.x);
        put_number(&mut out, "y", self.y);
        put_number(&mut out, "z", self.z);
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct CameraExtrinsicsTranslation {
    pub x: f64,
    pub y: f64,
    pub z: f64,
    pub raw: Map<String, Value>,
}

impl CameraExtrinsicsTranslation {
    pub fn from_json(value: &Value) -> std::result::Result<CameraExtrinsicsTranslation, DecodeError> {
        let obj = parse_object(value)?;
        Ok(CameraExtrinsicsTranslation {
            x: required(obj, "x", parse_number)?,
            y: required(obj, "y", parse_number)?,
            z: required(obj, "z", parse_number)?,
            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        put_number(&mut out, "x", self.x);
        put_number(&mut out, "y", self.y);
        put_number(&mut out, "z", self.z);
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct CameraExtrinsics {
    pub rotation: Option<CameraExtrinsicsRotation>,
    pub translation: Option<CameraExtrinsicsTranslation>,
    pub raw: Map<String, Value>,
}

impl CameraExtrinsics {
    pub fn from_json(value: &Value) -> std::result::Result<CameraExtrinsics, DecodeError> {
        let obj = parse_object(value)?;
        Ok(CameraExtrinsics {
            rotation: optional(obj, "rotation", CameraExtrinsicsRotation::from_json)?,
            translation: optional(obj, "translation", CameraExtrinsicsTranslation::from_json)?,
            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        if let Some(x) = &self.rotation {
            out.insert("rotation".to_string(), x.to_json());
        } else {
            out.remove("rotation");
        }
        if let Some(x) = &self.translation {
            out.insert("translation".to_string(), x.to_json());
        } else {
            out.remove("translation");
        }
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct Camera {
    pub intrinsics: Option<CameraIntrinsics>,
    pub hfovDegrees: Option<f64>,
    pub distortion: Option<CameraDistortion>,
    pub extrinsics: Option<CameraExtrinsics>,
    pub raw: Map<String, Value>,
}

impl Camera {
    pub fn from_json(value: &Value) -> std::result::Result<Camera, DecodeError> {
        let obj = parse_object(value)?;
        exactly_one(obj, &["intrinsics", "hfovDegrees"])?;
        Ok(Camera {
            intrinsics: optional(obj, "intrinsics", CameraIntrinsics::from_json)?,
            hfovDegrees: optional(obj, "hfovDegrees", limit(parse_number, |n| *n as f64, None, Some(0.0), Some(180.0)))?,
            distortion: optional(obj, "distortion", CameraDistortion::from_json)?,
            extrinsics: optional(obj, "extrinsics", CameraExtrinsics::from_json)?,
            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        if let Some(x) = &self.intrinsics {
            out.insert("intrinsics".to_string(), x.to_json());
        } else {
            out.remove("intrinsics");
        }
        if let Some(x) = &self.hfovDegrees {
            put_number(&mut out, "hfovDegrees", *x);
        } else {
            out.remove("hfovDegrees");
        }
        if let Some(x) = &self.distortion {
            out.insert("distortion".to_string(), x.to_json());
        } else {
            out.remove("distortion");
        }
        if let Some(x) = &self.extrinsics {
            out.insert("extrinsics".to_string(), x.to_json());
        } else {
            out.remove("extrinsics");
        }
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct ComponentParams {
    pub componentId: i64,
    pub values: Map<String, Value>,
    pub raw: Map<String, Value>,
}

impl ComponentParams {
    pub fn from_json(value: &Value) -> std::result::Result<ComponentParams, DecodeError> {
        let obj = parse_object(value)?;
        Ok(ComponentParams {
            componentId: required(obj, "componentId", parse_integer)?,
            values: required(obj, "values", parse_free)?,
            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        out.insert("componentId".to_string(), Value::from(*(&self.componentId)));
        out.insert("values".to_string(), Value::Object((&self.values).clone()));
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct Contour {
    pub points: Option<Vec<Point>>,
    pub cutouts: Option<Vec<Vec<Point>>>,
    pub raw: Map<String, Value>,
}

impl Contour {
    pub fn from_json(value: &Value) -> std::result::Result<Contour, DecodeError> {
        let obj = parse_object(value)?;
        Ok(Contour {
            points: optional(obj, "points", parse_array(Point::from_json))?,
            cutouts: optional(obj, "cutouts", parse_array(parse_array(Point::from_json)))?,
            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        if let Some(x) = &self.points {
            out.insert("points".to_string(), Value::Array(x.iter().map(|x| x.to_json()).collect()));
        } else {
            out.remove("points");
        }
        if let Some(x) = &self.cutouts {
            out.insert("cutouts".to_string(), Value::Array(x.iter().map(|x| Value::Array(x.iter().map(|x| x.to_json()).collect())).collect()));
        } else {
            out.remove("cutouts");
        }
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct Credit {
    pub id: String,
    pub bytes: i64,
    pub member: Option<i64>,
    pub raw: Map<String, Value>,
}

impl Credit {
    pub fn from_json(value: &Value) -> std::result::Result<Credit, DecodeError> {
        let obj = parse_object(value)?;
        required(obj, "type", parse_const("credit"))?;
        Ok(Credit {
            id: required(obj, "id", limit(parse_string, length, Some(1.0), None, None))?,
            bytes: required(obj, "bytes", limit(parse_integer, |n| *n as f64, Some(0.0), None, None))?,
            member: optional(obj, "member", limit(parse_integer, |n| *n as f64, Some(0.0), None, None))?,
            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        out.insert("id".to_string(), Value::String((&self.id).clone()));
        out.insert("bytes".to_string(), Value::from(*(&self.bytes)));
        if let Some(x) = &self.member {
            out.insert("member".to_string(), Value::from(*x));
        } else {
            out.remove("member");
        }
        out.insert("type".to_string(), Value::from("credit"));
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct Depth {
    pub width: Option<i64>,
    pub height: Option<i64>,
    pub semantic: Option<String>,
    pub values: Option<String>,
    pub world: Option<String>,
    pub raw: Map<String, Value>,
}

impl Depth {
    pub fn from_json(value: &Value) -> std::result::Result<Depth, DecodeError> {
        let obj = parse_object(value)?;
        Ok(Depth {
            width: optional(obj, "width", parse_integer)?,
            height: optional(obj, "height", parse_integer)?,
            semantic: optional(obj, "semantic", parse_string)?,
            values: optional(obj, "values", parse_string)?,
            world: optional(obj, "world", parse_string)?,
            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        if let Some(x) = &self.width {
            out.insert("width".to_string(), Value::from(*x));
        } else {
            out.remove("width");
        }
        if let Some(x) = &self.height {
            out.insert("height".to_string(), Value::from(*x));
        } else {
            out.remove("height");
        }
        if let Some(x) = &self.semantic {
            out.insert("semantic".to_string(), Value::String(x.clone()));
        } else {
            out.remove("semantic");
        }
        if let Some(x) = &self.values {
            out.insert("values".to_string(), Value::String(x.clone()));
        } else {
            out.remove("values");
        }
        if let Some(x) = &self.world {
            out.insert("world".to_string(), Value::String(x.clone()));
        } else {
            out.remove("world");
        }
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct Done {

    pub raw: Map<String, Value>,
}

impl Done {
    pub fn from_json(value: &Value) -> std::result::Result<Done, DecodeError> {
        let obj = parse_object(value)?;
        required(obj, "type", parse_const("done"))?;
        Ok(Done {

            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        out.insert("type".to_string(), Value::from("done"));
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct Dropped {
    pub id: String,
    pub count: i64,
    pub raw: Map<String, Value>,
}

impl Dropped {
    pub fn from_json(value: &Value) -> std::result::Result<Dropped, DecodeError> {
        let obj = parse_object(value)?;
        required(obj, "type", parse_const("dropped"))?;
        Ok(Dropped {
            id: required(obj, "id", limit(parse_string, length, Some(1.0), None, None))?,
            count: required(obj, "count", limit(parse_integer, |n| *n as f64, Some(0.0), None, None))?,
            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        out.insert("id".to_string(), Value::String((&self.id).clone()));
        out.insert("count".to_string(), Value::from(*(&self.count)));
        out.insert("type".to_string(), Value::from("dropped"));
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct End {
    pub id: String,
    pub reason: EndReason,
    pub message: Option<String>,
    pub milliComputeUnits: Option<i64>,
    pub raw: Map<String, Value>,
}

impl End {
    pub fn from_json(value: &Value) -> std::result::Result<End, DecodeError> {
        let obj = parse_object(value)?;
        required(obj, "type", parse_const("end"))?;
        Ok(End {
            id: required(obj, "id", limit(parse_string, length, Some(1.0), None, None))?,
            reason: required(obj, "reason", EndReason::from_json)?,
            message: optional(obj, "message", parse_string)?,
            milliComputeUnits: optional(obj, "milliComputeUnits", limit(parse_integer, |n| *n as f64, Some(0.0), None, None))?,
            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        out.insert("id".to_string(), Value::String((&self.id).clone()));
        out.insert("reason".to_string(), (&self.reason).to_json());
        if let Some(x) = &self.message {
            out.insert("message".to_string(), Value::String(x.clone()));
        } else {
            out.remove("message");
        }
        if let Some(x) = &self.milliComputeUnits {
            out.insert("milliComputeUnits".to_string(), Value::from(*x));
        } else {
            out.remove("milliComputeUnits");
        }
        out.insert("type".to_string(), Value::from("end"));
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct ErrorMessage {
    pub id: Option<String>,
    pub error: String,
    pub message: String,
    pub raw: Map<String, Value>,
}

impl ErrorMessage {
    pub fn from_json(value: &Value) -> std::result::Result<ErrorMessage, DecodeError> {
        let obj = parse_object(value)?;
        required(obj, "type", parse_const("error"))?;
        Ok(ErrorMessage {
            id: optional(obj, "id", limit(parse_string, length, Some(1.0), None, None))?,
            error: required(obj, "error", limit(parse_string, length, Some(1.0), None, None))?,
            message: required(obj, "message", parse_string)?,
            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        if let Some(x) = &self.id {
            out.insert("id".to_string(), Value::String(x.clone()));
        } else {
            out.remove("id");
        }
        out.insert("error".to_string(), Value::String((&self.error).clone()));
        out.insert("message".to_string(), Value::String((&self.message).clone()));
        out.insert("type".to_string(), Value::from("error"));
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct GetGraph {
    pub id: String,
    pub format: GetGraphFormat,
    pub verbose: Option<bool>,
    pub raw: Map<String, Value>,
}

impl GetGraph {
    pub fn from_json(value: &Value) -> std::result::Result<GetGraph, DecodeError> {
        let obj = parse_object(value)?;
        required(obj, "type", parse_const("getGraph"))?;
        Ok(GetGraph {
            id: required(obj, "id", limit(parse_string, length, Some(1.0), None, None))?,
            format: required(obj, "format", GetGraphFormat::from_json)?,
            verbose: optional(obj, "verbose", parse_boolean)?,
            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        out.insert("id".to_string(), Value::String((&self.id).clone()));
        out.insert("format".to_string(), (&self.format).to_json());
        if let Some(x) = &self.verbose {
            out.insert("verbose".to_string(), Value::Bool(*x));
        } else {
            out.remove("verbose");
        }
        out.insert("type".to_string(), Value::from("getGraph"));
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct InferenceComponent {
    pub ability: Option<String>,
    pub abilityUuid: Option<String>,
    pub params: Option<Map<String, Value>>,
    pub id: Option<i64>,
    pub raw: Map<String, Value>,
}

impl InferenceComponent {
    pub fn from_json(value: &Value) -> std::result::Result<InferenceComponent, DecodeError> {
        let obj = parse_object(value)?;
        required(obj, "type", parse_const("inference"))?;
        exactly_one(obj, &["ability", "abilityUuid"])?;
        Ok(InferenceComponent {
            ability: optional(obj, "ability", parse_string)?,
            abilityUuid: optional(obj, "abilityUuid", parse_string)?,
            params: optional(obj, "params", parse_free)?,
            id: optional(obj, "id", parse_integer)?,
            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        if let Some(x) = &self.ability {
            out.insert("ability".to_string(), Value::String(x.clone()));
        } else {
            out.remove("ability");
        }
        if let Some(x) = &self.abilityUuid {
            out.insert("abilityUuid".to_string(), Value::String(x.clone()));
        } else {
            out.remove("abilityUuid");
        }
        if let Some(x) = &self.params {
            out.insert("params".to_string(), Value::Object(x.clone()));
        } else {
            out.remove("params");
        }
        if let Some(x) = &self.id {
            out.insert("id".to_string(), Value::from(*x));
        } else {
            out.remove("id");
        }
        out.insert("type".to_string(), Value::from("inference"));
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct Mask {
    pub width: Option<i64>,
    pub height: Option<i64>,
    pub stride: Option<i64>,
    pub bitmap: Option<String>,
    pub world: Option<String>,
    pub raw: Map<String, Value>,
}

impl Mask {
    pub fn from_json(value: &Value) -> std::result::Result<Mask, DecodeError> {
        let obj = parse_object(value)?;
        Ok(Mask {
            width: optional(obj, "width", parse_integer)?,
            height: optional(obj, "height", parse_integer)?,
            stride: optional(obj, "stride", parse_integer)?,
            bitmap: optional(obj, "bitmap", parse_string)?,
            world: optional(obj, "world", parse_string)?,
            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        if let Some(x) = &self.width {
            out.insert("width".to_string(), Value::from(*x));
        } else {
            out.remove("width");
        }
        if let Some(x) = &self.height {
            out.insert("height".to_string(), Value::from(*x));
        } else {
            out.remove("height");
        }
        if let Some(x) = &self.stride {
            out.insert("stride".to_string(), Value::from(*x));
        } else {
            out.remove("stride");
        }
        if let Some(x) = &self.bitmap {
            out.insert("bitmap".to_string(), Value::String(x.clone()));
        } else {
            out.remove("bitmap");
        }
        if let Some(x) = &self.world {
            out.insert("world".to_string(), Value::String(x.clone()));
        } else {
            out.remove("world");
        }
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct Ping {
    pub id: String,
    pub raw: Map<String, Value>,
}

impl Ping {
    pub fn from_json(value: &Value) -> std::result::Result<Ping, DecodeError> {
        let obj = parse_object(value)?;
        required(obj, "type", parse_const("ping"))?;
        Ok(Ping {
            id: required(obj, "id", limit(parse_string, length, Some(1.0), None, None))?,
            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        out.insert("id".to_string(), Value::String((&self.id).clone()));
        out.insert("type".to_string(), Value::from("ping"));
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct Point {
    pub x: Option<f64>,
    pub y: Option<f64>,
    pub z: Option<f64>,
    pub worldX: Option<f64>,
    pub worldY: Option<f64>,
    pub worldZ: Option<f64>,
    pub raw: Map<String, Value>,
}

impl Point {
    pub fn from_json(value: &Value) -> std::result::Result<Point, DecodeError> {
        let obj = parse_object(value)?;
        Ok(Point {
            x: optional(obj, "x", parse_number)?,
            y: optional(obj, "y", parse_number)?,
            z: optional(obj, "z", parse_number)?,
            worldX: optional(obj, "worldX", parse_number)?,
            worldY: optional(obj, "worldY", parse_number)?,
            worldZ: optional(obj, "worldZ", parse_number)?,
            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        if let Some(x) = &self.x {
            put_number(&mut out, "x", *x);
        } else {
            out.remove("x");
        }
        if let Some(x) = &self.y {
            put_number(&mut out, "y", *x);
        } else {
            out.remove("y");
        }
        if let Some(x) = &self.z {
            put_number(&mut out, "z", *x);
        } else {
            out.remove("z");
        }
        if let Some(x) = &self.worldX {
            put_number(&mut out, "worldX", *x);
        } else {
            out.remove("worldX");
        }
        if let Some(x) = &self.worldY {
            put_number(&mut out, "worldY", *x);
        } else {
            out.remove("worldY");
        }
        if let Some(x) = &self.worldZ {
            put_number(&mut out, "worldZ", *x);
        } else {
            out.remove("worldZ");
        }
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct Pong {
    pub id: String,
    pub raw: Map<String, Value>,
}

impl Pong {
    pub fn from_json(value: &Value) -> std::result::Result<Pong, DecodeError> {
        let obj = parse_object(value)?;
        required(obj, "type", parse_const("pong"))?;
        Ok(Pong {
            id: required(obj, "id", limit(parse_string, length, Some(1.0), None, None))?,
            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        out.insert("id".to_string(), Value::String((&self.id).clone()));
        out.insert("type".to_string(), Value::from("pong"));
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct Pop {
    pub components: Vec<PopComponent>,
    pub postTransform: Option<String>,
    pub defaults: Option<SourceDefaults>,
    pub depthMap: Option<PopDepthMap>,
    pub raw: Map<String, Value>,
}

impl Pop {
    pub fn from_json(value: &Value) -> std::result::Result<Pop, DecodeError> {
        let obj = parse_object(value)?;
        Ok(Pop {
            components: required(obj, "components", parse_array(PopComponent::from_json))?,
            postTransform: optional(obj, "postTransform", parse_string)?,
            defaults: optional(obj, "defaults", SourceDefaults::from_json)?,
            depthMap: optional(obj, "depthMap", PopDepthMap::from_json)?,
            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        out.insert("components".to_string(), Value::Array((&self.components).iter().map(|x| x.to_json()).collect()));
        if let Some(x) = &self.postTransform {
            out.insert("postTransform".to_string(), Value::String(x.clone()));
        } else {
            out.remove("postTransform");
        }
        if let Some(x) = &self.defaults {
            out.insert("defaults".to_string(), x.to_json());
        } else {
            out.remove("defaults");
        }
        if let Some(x) = &self.depthMap {
            out.insert("depthMap".to_string(), x.to_json());
        } else {
            out.remove("depthMap");
        }
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct PopDepthMap {
    pub ability: Option<String>,
    pub abilityUuid: Option<String>,
    pub toWorld: Option<bool>,
    pub raw: Map<String, Value>,
}

impl PopDepthMap {
    pub fn from_json(value: &Value) -> std::result::Result<PopDepthMap, DecodeError> {
        let obj = parse_object(value)?;
        exactly_one(obj, &["ability", "abilityUuid"])?;
        Ok(PopDepthMap {
            ability: optional(obj, "ability", parse_string)?,
            abilityUuid: optional(obj, "abilityUuid", parse_string)?,
            toWorld: optional(obj, "toWorld", parse_boolean)?,
            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        if let Some(x) = &self.ability {
            out.insert("ability".to_string(), Value::String(x.clone()));
        } else {
            out.remove("ability");
        }
        if let Some(x) = &self.abilityUuid {
            out.insert("abilityUuid".to_string(), Value::String(x.clone()));
        } else {
            out.remove("abilityUuid");
        }
        if let Some(x) = &self.toWorld {
            out.insert("toWorld".to_string(), Value::Bool(*x));
        } else {
            out.remove("toWorld");
        }
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct PredictedClass {
    pub classLabel: Option<String>,
    pub confidence: Option<f64>,
    pub category: Option<String>,
    pub raw: Map<String, Value>,
}

impl PredictedClass {
    pub fn from_json(value: &Value) -> std::result::Result<PredictedClass, DecodeError> {
        let obj = parse_object(value)?;
        Ok(PredictedClass {
            classLabel: optional(obj, "classLabel", parse_string)?,
            confidence: optional(obj, "confidence", parse_number)?,
            category: optional(obj, "category", parse_string)?,
            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        if let Some(x) = &self.classLabel {
            out.insert("classLabel".to_string(), Value::String(x.clone()));
        } else {
            out.remove("classLabel");
        }
        if let Some(x) = &self.confidence {
            put_number(&mut out, "confidence", *x);
        } else {
            out.remove("confidence");
        }
        if let Some(x) = &self.category {
            out.insert("category".to_string(), Value::String(x.clone()));
        } else {
            out.remove("category");
        }
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct PredictedKeyPoint {
    pub x: Option<f64>,
    pub y: Option<f64>,
    pub z: Option<f64>,
    pub worldX: Option<f64>,
    pub worldY: Option<f64>,
    pub worldZ: Option<f64>,
    pub classLabel: Option<String>,
    pub confidence: Option<f64>,
    pub category: Option<String>,
    pub visible: Option<bool>,
    pub raw: Map<String, Value>,
}

impl PredictedKeyPoint {
    pub fn from_json(value: &Value) -> std::result::Result<PredictedKeyPoint, DecodeError> {
        let obj = parse_object(value)?;
        Ok(PredictedKeyPoint {
            x: optional(obj, "x", parse_number)?,
            y: optional(obj, "y", parse_number)?,
            z: optional(obj, "z", parse_number)?,
            worldX: optional(obj, "worldX", parse_number)?,
            worldY: optional(obj, "worldY", parse_number)?,
            worldZ: optional(obj, "worldZ", parse_number)?,
            classLabel: optional(obj, "classLabel", parse_string)?,
            confidence: optional(obj, "confidence", parse_number)?,
            category: optional(obj, "category", parse_string)?,
            visible: optional(obj, "visible", parse_boolean)?,
            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        if let Some(x) = &self.x {
            put_number(&mut out, "x", *x);
        } else {
            out.remove("x");
        }
        if let Some(x) = &self.y {
            put_number(&mut out, "y", *x);
        } else {
            out.remove("y");
        }
        if let Some(x) = &self.z {
            put_number(&mut out, "z", *x);
        } else {
            out.remove("z");
        }
        if let Some(x) = &self.worldX {
            put_number(&mut out, "worldX", *x);
        } else {
            out.remove("worldX");
        }
        if let Some(x) = &self.worldY {
            put_number(&mut out, "worldY", *x);
        } else {
            out.remove("worldY");
        }
        if let Some(x) = &self.worldZ {
            put_number(&mut out, "worldZ", *x);
        } else {
            out.remove("worldZ");
        }
        if let Some(x) = &self.classLabel {
            out.insert("classLabel".to_string(), Value::String(x.clone()));
        } else {
            out.remove("classLabel");
        }
        if let Some(x) = &self.confidence {
            put_number(&mut out, "confidence", *x);
        } else {
            out.remove("confidence");
        }
        if let Some(x) = &self.category {
            out.insert("category".to_string(), Value::String(x.clone()));
        } else {
            out.remove("category");
        }
        if let Some(x) = &self.visible {
            out.insert("visible".to_string(), Value::Bool(*x));
        } else {
            out.remove("visible");
        }
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct PredictedKeyPoints {
    pub confidence: Option<f64>,
    pub category: Option<String>,
    pub points: Option<Vec<PredictedKeyPoint>>,
    pub raw: Map<String, Value>,
}

impl PredictedKeyPoints {
    pub fn from_json(value: &Value) -> std::result::Result<PredictedKeyPoints, DecodeError> {
        let obj = parse_object(value)?;
        Ok(PredictedKeyPoints {
            confidence: optional(obj, "confidence", parse_number)?,
            category: optional(obj, "category", parse_string)?,
            points: optional(obj, "points", parse_array(PredictedKeyPoint::from_json))?,
            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        if let Some(x) = &self.confidence {
            put_number(&mut out, "confidence", *x);
        } else {
            out.remove("confidence");
        }
        if let Some(x) = &self.category {
            out.insert("category".to_string(), Value::String(x.clone()));
        } else {
            out.remove("category");
        }
        if let Some(x) = &self.points {
            out.insert("points".to_string(), Value::Array(x.iter().map(|x| x.to_json()).collect()));
        } else {
            out.remove("points");
        }
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct PredictedMesh {
    pub confidence: Option<f64>,
    pub category: Option<String>,
    pub points: Option<Vec<Point>>,
    pub raw: Map<String, Value>,
}

impl PredictedMesh {
    pub fn from_json(value: &Value) -> std::result::Result<PredictedMesh, DecodeError> {
        let obj = parse_object(value)?;
        Ok(PredictedMesh {
            confidence: optional(obj, "confidence", parse_number)?,
            category: optional(obj, "category", parse_string)?,
            points: optional(obj, "points", parse_array(Point::from_json))?,
            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        if let Some(x) = &self.confidence {
            put_number(&mut out, "confidence", *x);
        } else {
            out.remove("confidence");
        }
        if let Some(x) = &self.category {
            out.insert("category".to_string(), Value::String(x.clone()));
        } else {
            out.remove("category");
        }
        if let Some(x) = &self.points {
            out.insert("points".to_string(), Value::Array(x.iter().map(|x| x.to_json()).collect()));
        } else {
            out.remove("points");
        }
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct PredictedObject {
    pub classLabel: Option<String>,
    pub confidence: Option<f64>,
    pub category: Option<String>,
    pub x: Option<f64>,
    pub y: Option<f64>,
    pub width: Option<f64>,
    pub height: Option<f64>,
    pub orientation: Option<f64>,
    pub trackId: Option<i64>,
    pub globalObjectId: Option<i64>,
    pub outline: Option<Vec<Point>>,
    pub contours: Option<Vec<Contour>>,
    pub mask: Option<Mask>,
    pub objects: Option<Vec<PredictedObject>>,
    pub classes: Option<Vec<PredictedClass>>,
    pub texts: Option<Vec<PredictedText>>,
    pub keyPoints: Option<Vec<PredictedKeyPoints>>,
    pub meshes: Option<Vec<PredictedMesh>>,
    pub details: Option<Vec<Map<String, Value>>>,
    pub raw: Map<String, Value>,
}

impl PredictedObject {
    pub fn from_json(value: &Value) -> std::result::Result<PredictedObject, DecodeError> {
        let obj = parse_object(value)?;
        Ok(PredictedObject {
            classLabel: optional(obj, "classLabel", parse_string)?,
            confidence: optional(obj, "confidence", parse_number)?,
            category: optional(obj, "category", parse_string)?,
            x: optional(obj, "x", parse_number)?,
            y: optional(obj, "y", parse_number)?,
            width: optional(obj, "width", parse_number)?,
            height: optional(obj, "height", parse_number)?,
            orientation: optional(obj, "orientation", parse_number)?,
            trackId: optional(obj, "trackId", parse_integer)?,
            globalObjectId: optional(obj, "globalObjectId", parse_integer)?,
            outline: optional(obj, "outline", parse_array(Point::from_json))?,
            contours: optional(obj, "contours", parse_array(Contour::from_json))?,
            mask: optional(obj, "mask", Mask::from_json)?,
            objects: optional(obj, "objects", parse_array(PredictedObject::from_json))?,
            classes: optional(obj, "classes", parse_array(PredictedClass::from_json))?,
            texts: optional(obj, "texts", parse_array(PredictedText::from_json))?,
            keyPoints: optional(obj, "keyPoints", parse_array(PredictedKeyPoints::from_json))?,
            meshes: optional(obj, "meshes", parse_array(PredictedMesh::from_json))?,
            details: optional(obj, "details", parse_array(parse_free))?,
            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        if let Some(x) = &self.classLabel {
            out.insert("classLabel".to_string(), Value::String(x.clone()));
        } else {
            out.remove("classLabel");
        }
        if let Some(x) = &self.confidence {
            put_number(&mut out, "confidence", *x);
        } else {
            out.remove("confidence");
        }
        if let Some(x) = &self.category {
            out.insert("category".to_string(), Value::String(x.clone()));
        } else {
            out.remove("category");
        }
        if let Some(x) = &self.x {
            put_number(&mut out, "x", *x);
        } else {
            out.remove("x");
        }
        if let Some(x) = &self.y {
            put_number(&mut out, "y", *x);
        } else {
            out.remove("y");
        }
        if let Some(x) = &self.width {
            put_number(&mut out, "width", *x);
        } else {
            out.remove("width");
        }
        if let Some(x) = &self.height {
            put_number(&mut out, "height", *x);
        } else {
            out.remove("height");
        }
        if let Some(x) = &self.orientation {
            put_number(&mut out, "orientation", *x);
        } else {
            out.remove("orientation");
        }
        if let Some(x) = &self.trackId {
            out.insert("trackId".to_string(), Value::from(*x));
        } else {
            out.remove("trackId");
        }
        if let Some(x) = &self.globalObjectId {
            out.insert("globalObjectId".to_string(), Value::from(*x));
        } else {
            out.remove("globalObjectId");
        }
        if let Some(x) = &self.outline {
            out.insert("outline".to_string(), Value::Array(x.iter().map(|x| x.to_json()).collect()));
        } else {
            out.remove("outline");
        }
        if let Some(x) = &self.contours {
            out.insert("contours".to_string(), Value::Array(x.iter().map(|x| x.to_json()).collect()));
        } else {
            out.remove("contours");
        }
        if let Some(x) = &self.mask {
            out.insert("mask".to_string(), x.to_json());
        } else {
            out.remove("mask");
        }
        if let Some(x) = &self.objects {
            out.insert("objects".to_string(), Value::Array(x.iter().map(|x| x.to_json()).collect()));
        } else {
            out.remove("objects");
        }
        if let Some(x) = &self.classes {
            out.insert("classes".to_string(), Value::Array(x.iter().map(|x| x.to_json()).collect()));
        } else {
            out.remove("classes");
        }
        if let Some(x) = &self.texts {
            out.insert("texts".to_string(), Value::Array(x.iter().map(|x| x.to_json()).collect()));
        } else {
            out.remove("texts");
        }
        if let Some(x) = &self.keyPoints {
            out.insert("keyPoints".to_string(), Value::Array(x.iter().map(|x| x.to_json()).collect()));
        } else {
            out.remove("keyPoints");
        }
        if let Some(x) = &self.meshes {
            out.insert("meshes".to_string(), Value::Array(x.iter().map(|x| x.to_json()).collect()));
        } else {
            out.remove("meshes");
        }
        if let Some(x) = &self.details {
            out.insert("details".to_string(), Value::Array(x.iter().map(|x| Value::Object(x.clone())).collect()));
        } else {
            out.remove("details");
        }
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct PredictedText {
    pub text: Option<String>,
    pub confidence: Option<f64>,
    pub category: Option<String>,
    pub raw: Map<String, Value>,
}

impl PredictedText {
    pub fn from_json(value: &Value) -> std::result::Result<PredictedText, DecodeError> {
        let obj = parse_object(value)?;
        Ok(PredictedText {
            text: optional(obj, "text", parse_string)?,
            confidence: optional(obj, "confidence", parse_number)?,
            category: optional(obj, "category", parse_string)?,
            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        if let Some(x) = &self.text {
            out.insert("text".to_string(), Value::String(x.clone()));
        } else {
            out.remove("text");
        }
        if let Some(x) = &self.confidence {
            put_number(&mut out, "confidence", *x);
        } else {
            out.remove("confidence");
        }
        if let Some(x) = &self.category {
            out.insert("category".to_string(), Value::String(x.clone()));
        } else {
            out.remove("category");
        }
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct Prediction {
    pub timestamp: Option<i64>,
    pub seconds: Option<f64>,
    pub offset: Option<i64>,
    pub duration: Option<i64>,
    pub captured_at: Option<i64>,
    pub source_id: Option<String>,
    pub source_width: Option<i64>,
    pub source_height: Option<i64>,
    pub compute_units: Option<f64>,
    pub milli_compute_units: Option<i64>,
    pub selected: Option<bool>,
    pub objects: Option<Vec<PredictedObject>>,
    pub classes: Option<Vec<PredictedClass>>,
    pub texts: Option<Vec<PredictedText>>,
    pub keyPoints: Option<Vec<PredictedKeyPoints>>,
    pub meshes: Option<Vec<PredictedMesh>>,
    pub depth: Option<Depth>,
    pub tokens: Option<Map<String, Value>>,
    pub details: Option<Vec<Map<String, Value>>>,
    pub track_events: Option<Vec<TrackEvent>>,
    pub raw: Map<String, Value>,
}

impl Prediction {
    pub fn from_json(value: &Value) -> std::result::Result<Prediction, DecodeError> {
        let obj = parse_object(value)?;
        Ok(Prediction {
            timestamp: optional(obj, "timestamp", parse_integer)?,
            seconds: optional(obj, "seconds", parse_number)?,
            offset: optional(obj, "offset", parse_integer)?,
            duration: optional(obj, "duration", parse_integer)?,
            captured_at: optional(obj, "captured_at", parse_integer)?,
            source_id: optional(obj, "source_id", parse_string)?,
            source_width: optional(obj, "source_width", parse_integer)?,
            source_height: optional(obj, "source_height", parse_integer)?,
            compute_units: optional(obj, "compute_units", parse_number)?,
            milli_compute_units: optional(obj, "milli_compute_units", parse_integer)?,
            selected: optional(obj, "selected", parse_boolean)?,
            objects: optional(obj, "objects", parse_array(PredictedObject::from_json))?,
            classes: optional(obj, "classes", parse_array(PredictedClass::from_json))?,
            texts: optional(obj, "texts", parse_array(PredictedText::from_json))?,
            keyPoints: optional(obj, "keyPoints", parse_array(PredictedKeyPoints::from_json))?,
            meshes: optional(obj, "meshes", parse_array(PredictedMesh::from_json))?,
            depth: optional(obj, "depth", Depth::from_json)?,
            tokens: optional(obj, "tokens", parse_free)?,
            details: optional(obj, "details", parse_array(parse_free))?,
            track_events: optional(obj, "track_events", parse_array(TrackEvent::from_json))?,
            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        if let Some(x) = &self.timestamp {
            out.insert("timestamp".to_string(), Value::from(*x));
        } else {
            out.remove("timestamp");
        }
        if let Some(x) = &self.seconds {
            put_number(&mut out, "seconds", *x);
        } else {
            out.remove("seconds");
        }
        if let Some(x) = &self.offset {
            out.insert("offset".to_string(), Value::from(*x));
        } else {
            out.remove("offset");
        }
        if let Some(x) = &self.duration {
            out.insert("duration".to_string(), Value::from(*x));
        } else {
            out.remove("duration");
        }
        if let Some(x) = &self.captured_at {
            out.insert("captured_at".to_string(), Value::from(*x));
        } else {
            out.remove("captured_at");
        }
        if let Some(x) = &self.source_id {
            out.insert("source_id".to_string(), Value::String(x.clone()));
        } else {
            out.remove("source_id");
        }
        if let Some(x) = &self.source_width {
            out.insert("source_width".to_string(), Value::from(*x));
        } else {
            out.remove("source_width");
        }
        if let Some(x) = &self.source_height {
            out.insert("source_height".to_string(), Value::from(*x));
        } else {
            out.remove("source_height");
        }
        if let Some(x) = &self.compute_units {
            put_number(&mut out, "compute_units", *x);
        } else {
            out.remove("compute_units");
        }
        if let Some(x) = &self.milli_compute_units {
            out.insert("milli_compute_units".to_string(), Value::from(*x));
        } else {
            out.remove("milli_compute_units");
        }
        if let Some(x) = &self.selected {
            out.insert("selected".to_string(), Value::Bool(*x));
        } else {
            out.remove("selected");
        }
        if let Some(x) = &self.objects {
            out.insert("objects".to_string(), Value::Array(x.iter().map(|x| x.to_json()).collect()));
        } else {
            out.remove("objects");
        }
        if let Some(x) = &self.classes {
            out.insert("classes".to_string(), Value::Array(x.iter().map(|x| x.to_json()).collect()));
        } else {
            out.remove("classes");
        }
        if let Some(x) = &self.texts {
            out.insert("texts".to_string(), Value::Array(x.iter().map(|x| x.to_json()).collect()));
        } else {
            out.remove("texts");
        }
        if let Some(x) = &self.keyPoints {
            out.insert("keyPoints".to_string(), Value::Array(x.iter().map(|x| x.to_json()).collect()));
        } else {
            out.remove("keyPoints");
        }
        if let Some(x) = &self.meshes {
            out.insert("meshes".to_string(), Value::Array(x.iter().map(|x| x.to_json()).collect()));
        } else {
            out.remove("meshes");
        }
        if let Some(x) = &self.depth {
            out.insert("depth".to_string(), x.to_json());
        } else {
            out.remove("depth");
        }
        if let Some(x) = &self.tokens {
            out.insert("tokens".to_string(), Value::Object(x.clone()));
        } else {
            out.remove("tokens");
        }
        if let Some(x) = &self.details {
            out.insert("details".to_string(), Value::Array(x.iter().map(|x| Value::Object(x.clone())).collect()));
        } else {
            out.remove("details");
        }
        if let Some(x) = &self.track_events {
            out.insert("track_events".to_string(), Value::Array(x.iter().map(|x| x.to_json()).collect()));
        } else {
            out.remove("track_events");
        }
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct PredictionMessage {
    pub id: String,
    pub prediction: Prediction,
    pub raw: Map<String, Value>,
}

impl PredictionMessage {
    pub fn from_json(value: &Value) -> std::result::Result<PredictionMessage, DecodeError> {
        let obj = parse_object(value)?;
        required(obj, "type", parse_const("prediction"))?;
        Ok(PredictionMessage {
            id: required(obj, "id", limit(parse_string, length, Some(1.0), None, None))?,
            prediction: required(obj, "prediction", Prediction::from_json)?,
            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        out.insert("id".to_string(), Value::String((&self.id).clone()));
        out.insert("prediction".to_string(), (&self.prediction).to_json());
        out.insert("type".to_string(), Value::from("prediction"));
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct Quit {
    pub id: String,
    pub raw: Map<String, Value>,
}

impl Quit {
    pub fn from_json(value: &Value) -> std::result::Result<Quit, DecodeError> {
        let obj = parse_object(value)?;
        required(obj, "type", parse_const("quit"))?;
        Ok(Quit {
            id: required(obj, "id", limit(parse_string, length, Some(1.0), None, None))?,
            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        out.insert("id".to_string(), Value::String((&self.id).clone()));
        out.insert("type".to_string(), Value::from("quit"));
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct RawComponent {
    pub r#type: String,
    pub raw: Map<String, Value>,
}

impl RawComponent {
    pub fn from_json(value: &Value) -> std::result::Result<RawComponent, DecodeError> {
        let obj = parse_object(value)?;
        Ok(RawComponent {
            r#type: required(obj, "type", parse_string)?,
            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        out.insert("type".to_string(), Value::String((&self.r#type).clone()));
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct Result {
    pub id: String,
    pub raw: Map<String, Value>,
}

impl Result {
    pub fn from_json(value: &Value) -> std::result::Result<Result, DecodeError> {
        let obj = parse_object(value)?;
        required(obj, "type", parse_const("result"))?;
        Ok(Result {
            id: required(obj, "id", limit(parse_string, length, Some(1.0), None, None))?,
            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        out.insert("id".to_string(), Value::String((&self.id).clone()));
        out.insert("type".to_string(), Value::from("result"));
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct Send {
    pub id: String,
    pub credit: i64,
    pub member: Option<i64>,
    pub raw: Map<String, Value>,
}

impl Send {
    pub fn from_json(value: &Value) -> std::result::Result<Send, DecodeError> {
        let obj = parse_object(value)?;
        required(obj, "type", parse_const("send"))?;
        Ok(Send {
            id: required(obj, "id", limit(parse_string, length, Some(1.0), None, None))?,
            credit: required(obj, "credit", limit(parse_integer, |n| *n as f64, Some(0.0), None, None))?,
            member: optional(obj, "member", limit(parse_integer, |n| *n as f64, Some(0.0), None, None))?,
            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        out.insert("id".to_string(), Value::String((&self.id).clone()));
        out.insert("credit".to_string(), Value::from(*(&self.credit)));
        if let Some(x) = &self.member {
            out.insert("member".to_string(), Value::from(*x));
        } else {
            out.remove("member");
        }
        out.insert("type".to_string(), Value::from("send"));
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct SetPop {
    pub id: String,
    pub pop: Pop,
    pub raw: Map<String, Value>,
}

impl SetPop {
    pub fn from_json(value: &Value) -> std::result::Result<SetPop, DecodeError> {
        let obj = parse_object(value)?;
        required(obj, "type", parse_const("setPop"))?;
        Ok(SetPop {
            id: required(obj, "id", limit(parse_string, length, Some(1.0), None, None))?,
            pop: required(obj, "pop", Pop::from_json)?,
            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        out.insert("id".to_string(), Value::String((&self.id).clone()));
        out.insert("pop".to_string(), (&self.pop).to_json());
        out.insert("type".to_string(), Value::from("setPop"));
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct SetSourceUpload {
    pub contentType: String,
    pub raw: Map<String, Value>,
}

impl SetSourceUpload {
    pub fn from_json(value: &Value) -> std::result::Result<SetSourceUpload, DecodeError> {
        let obj = parse_object(value)?;
        Ok(SetSourceUpload {
            contentType: required(obj, "contentType", parse_string)?,
            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        out.insert("contentType".to_string(), Value::String((&self.contentType).clone()));
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct SetSource {
    pub id: String,
    pub url: Option<String>,
    pub assetUuid: Option<String>,
    pub upload: Option<SetSourceUpload>,
    pub group: Option<Vec<GroupMember>>,
    pub params: Option<Vec<ComponentParams>>,
    pub fps: Option<String>,
    pub roi: Option<Roi>,
    pub camera: Option<Camera>,
    pub live: Option<bool>,
    pub mode: Option<SetSourceMode>,
    pub raw: Map<String, Value>,
}

impl SetSource {
    pub fn from_json(value: &Value) -> std::result::Result<SetSource, DecodeError> {
        let obj = parse_object(value)?;
        required(obj, "type", parse_const("setSource"))?;
        exactly_one(obj, &["url", "assetUuid", "upload", "group"])?;
        Ok(SetSource {
            id: required(obj, "id", limit(parse_string, length, Some(1.0), None, None))?,
            url: optional(obj, "url", parse_string)?,
            assetUuid: optional(obj, "assetUuid", parse_string)?,
            upload: optional(obj, "upload", SetSourceUpload::from_json)?,
            group: optional(obj, "group", parse_array(GroupMember::from_json))?,
            params: optional(obj, "params", parse_array(ComponentParams::from_json))?,
            fps: optional(obj, "fps", parse_string)?,
            roi: optional(obj, "roi", Roi::from_json)?,
            camera: optional(obj, "camera", Camera::from_json)?,
            live: optional(obj, "live", parse_boolean)?,
            mode: optional(obj, "mode", SetSourceMode::from_json)?,
            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        out.insert("id".to_string(), Value::String((&self.id).clone()));
        if let Some(x) = &self.url {
            out.insert("url".to_string(), Value::String(x.clone()));
        } else {
            out.remove("url");
        }
        if let Some(x) = &self.assetUuid {
            out.insert("assetUuid".to_string(), Value::String(x.clone()));
        } else {
            out.remove("assetUuid");
        }
        if let Some(x) = &self.upload {
            out.insert("upload".to_string(), x.to_json());
        } else {
            out.remove("upload");
        }
        if let Some(x) = &self.group {
            out.insert("group".to_string(), Value::Array(x.iter().map(|x| x.to_json()).collect()));
        } else {
            out.remove("group");
        }
        if let Some(x) = &self.params {
            out.insert("params".to_string(), Value::Array(x.iter().map(|x| x.to_json()).collect()));
        } else {
            out.remove("params");
        }
        if let Some(x) = &self.fps {
            out.insert("fps".to_string(), Value::String(x.clone()));
        } else {
            out.remove("fps");
        }
        if let Some(x) = &self.roi {
            out.insert("roi".to_string(), x.to_json());
        } else {
            out.remove("roi");
        }
        if let Some(x) = &self.camera {
            out.insert("camera".to_string(), x.to_json());
        } else {
            out.remove("camera");
        }
        if let Some(x) = &self.live {
            out.insert("live".to_string(), Value::Bool(*x));
        } else {
            out.remove("live");
        }
        if let Some(x) = &self.mode {
            out.insert("mode".to_string(), x.to_json());
        } else {
            out.remove("mode");
        }
        out.insert("type".to_string(), Value::from("setSource"));
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct SourceDefaults {
    pub camera: Option<Camera>,
    pub fps: Option<String>,
    pub roi: Option<Roi>,
    pub motionDetect: Option<bool>,
    pub motionSensitivity: Option<f64>,
    pub motionThreshold: Option<f64>,
    pub motionGap: Option<i64>,
    pub motionGridX: Option<i64>,
    pub motionGridY: Option<i64>,
    pub raw: Map<String, Value>,
}

impl SourceDefaults {
    pub fn from_json(value: &Value) -> std::result::Result<SourceDefaults, DecodeError> {
        let obj = parse_object(value)?;
        Ok(SourceDefaults {
            camera: optional(obj, "camera", Camera::from_json)?,
            fps: optional(obj, "fps", parse_string)?,
            roi: optional(obj, "roi", Roi::from_json)?,
            motionDetect: optional(obj, "motionDetect", parse_boolean)?,
            motionSensitivity: optional(obj, "motionSensitivity", parse_number)?,
            motionThreshold: optional(obj, "motionThreshold", parse_number)?,
            motionGap: optional(obj, "motionGap", parse_integer)?,
            motionGridX: optional(obj, "motionGridX", parse_integer)?,
            motionGridY: optional(obj, "motionGridY", parse_integer)?,
            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        if let Some(x) = &self.camera {
            out.insert("camera".to_string(), x.to_json());
        } else {
            out.remove("camera");
        }
        if let Some(x) = &self.fps {
            out.insert("fps".to_string(), Value::String(x.clone()));
        } else {
            out.remove("fps");
        }
        if let Some(x) = &self.roi {
            out.insert("roi".to_string(), x.to_json());
        } else {
            out.remove("roi");
        }
        if let Some(x) = &self.motionDetect {
            out.insert("motionDetect".to_string(), Value::Bool(*x));
        } else {
            out.remove("motionDetect");
        }
        if let Some(x) = &self.motionSensitivity {
            put_number(&mut out, "motionSensitivity", *x);
        } else {
            out.remove("motionSensitivity");
        }
        if let Some(x) = &self.motionThreshold {
            put_number(&mut out, "motionThreshold", *x);
        } else {
            out.remove("motionThreshold");
        }
        if let Some(x) = &self.motionGap {
            out.insert("motionGap".to_string(), Value::from(*x));
        } else {
            out.remove("motionGap");
        }
        if let Some(x) = &self.motionGridX {
            out.insert("motionGridX".to_string(), Value::from(*x));
        } else {
            out.remove("motionGridX");
        }
        if let Some(x) = &self.motionGridY {
            out.insert("motionGridY".to_string(), Value::from(*x));
        } else {
            out.remove("motionGridY");
        }
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct Start {
    pub id: String,
    pub raw: Map<String, Value>,
}

impl Start {
    pub fn from_json(value: &Value) -> std::result::Result<Start, DecodeError> {
        let obj = parse_object(value)?;
        required(obj, "type", parse_const("start"))?;
        Ok(Start {
            id: required(obj, "id", limit(parse_string, length, Some(1.0), None, None))?,
            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        out.insert("id".to_string(), Value::String((&self.id).clone()));
        out.insert("type".to_string(), Value::from("start"));
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct StopSource {
    pub id: String,
    pub raw: Map<String, Value>,
}

impl StopSource {
    pub fn from_json(value: &Value) -> std::result::Result<StopSource, DecodeError> {
        let obj = parse_object(value)?;
        required(obj, "type", parse_const("stopSource"))?;
        Ok(StopSource {
            id: required(obj, "id", limit(parse_string, length, Some(1.0), None, None))?,
            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        out.insert("id".to_string(), Value::String((&self.id).clone()));
        out.insert("type".to_string(), Value::from("stopSource"));
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct TrackEvent {
    pub track_id: Option<i64>,
    pub is_ended: Option<bool>,
    pub started_at: Option<i64>,
    pub ended_at: Option<i64>,
    pub raw: Map<String, Value>,
}

impl TrackEvent {
    pub fn from_json(value: &Value) -> std::result::Result<TrackEvent, DecodeError> {
        let obj = parse_object(value)?;
        Ok(TrackEvent {
            track_id: optional(obj, "track_id", parse_integer)?,
            is_ended: optional(obj, "is_ended", parse_boolean)?,
            started_at: optional(obj, "started_at", parse_integer)?,
            ended_at: optional(obj, "ended_at", parse_integer)?,
            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        if let Some(x) = &self.track_id {
            out.insert("track_id".to_string(), Value::from(*x));
        } else {
            out.remove("track_id");
        }
        if let Some(x) = &self.is_ended {
            out.insert("is_ended".to_string(), Value::Bool(*x));
        } else {
            out.remove("is_ended");
        }
        if let Some(x) = &self.started_at {
            out.insert("started_at".to_string(), Value::from(*x));
        } else {
            out.remove("started_at");
        }
        if let Some(x) = &self.ended_at {
            out.insert("ended_at".to_string(), Value::from(*x));
        } else {
            out.remove("ended_at");
        }
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct Uploaded {
    pub id: String,
    pub member: Option<i64>,
    pub raw: Map<String, Value>,
}

impl Uploaded {
    pub fn from_json(value: &Value) -> std::result::Result<Uploaded, DecodeError> {
        let obj = parse_object(value)?;
        required(obj, "type", parse_const("uploaded"))?;
        Ok(Uploaded {
            id: required(obj, "id", limit(parse_string, length, Some(1.0), None, None))?,
            member: optional(obj, "member", limit(parse_integer, |n| *n as f64, Some(0.0), None, None))?,
            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        out.insert("id".to_string(), Value::String((&self.id).clone()));
        if let Some(x) = &self.member {
            out.insert("member".to_string(), Value::from(*x));
        } else {
            out.remove("member");
        }
        out.insert("type".to_string(), Value::from("uploaded"));
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct Usage {
    pub id: String,
    pub milliComputeUnits: i64,
    pub raw: Map<String, Value>,
}

impl Usage {
    pub fn from_json(value: &Value) -> std::result::Result<Usage, DecodeError> {
        let obj = parse_object(value)?;
        required(obj, "type", parse_const("usage"))?;
        Ok(Usage {
            id: required(obj, "id", limit(parse_string, length, Some(1.0), None, None))?,
            milliComputeUnits: required(obj, "milliComputeUnits", limit(parse_integer, |n| *n as f64, Some(0.0), None, None))?,
            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        out.insert("id".to_string(), Value::String((&self.id).clone()));
        out.insert("milliComputeUnits".to_string(), Value::from(*(&self.milliComputeUnits)));
        out.insert("type".to_string(), Value::from("usage"));
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct GroupMemberUrl {
    pub url: String,
    pub raw: Map<String, Value>,
}

impl GroupMemberUrl {
    pub fn from_json(value: &Value) -> std::result::Result<GroupMemberUrl, DecodeError> {
        let obj = parse_object(value)?;
        Ok(GroupMemberUrl {
            url: required(obj, "url", parse_string)?,
            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        out.insert("url".to_string(), Value::String((&self.url).clone()));
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct GroupMemberUploadUpload {
    pub contentType: String,
    pub bytes: Option<i64>,
    pub raw: Map<String, Value>,
}

impl GroupMemberUploadUpload {
    pub fn from_json(value: &Value) -> std::result::Result<GroupMemberUploadUpload, DecodeError> {
        let obj = parse_object(value)?;
        Ok(GroupMemberUploadUpload {
            contentType: required(obj, "contentType", parse_string)?,
            bytes: optional(obj, "bytes", limit(parse_integer, |n| *n as f64, Some(0.0), None, None))?,
            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        out.insert("contentType".to_string(), Value::String((&self.contentType).clone()));
        if let Some(x) = &self.bytes {
            out.insert("bytes".to_string(), Value::from(*x));
        } else {
            out.remove("bytes");
        }
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct GroupMemberUpload {
    pub upload: GroupMemberUploadUpload,
    pub raw: Map<String, Value>,
}

impl GroupMemberUpload {
    pub fn from_json(value: &Value) -> std::result::Result<GroupMemberUpload, DecodeError> {
        let obj = parse_object(value)?;
        Ok(GroupMemberUpload {
            upload: required(obj, "upload", GroupMemberUploadUpload::from_json)?,
            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        out.insert("upload".to_string(), (&self.upload).to_json());
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct RoiRectangle {
    pub x: f64,
    pub y: f64,
    pub width: f64,
    pub height: f64,
    pub raw: Map<String, Value>,
}

impl RoiRectangle {
    pub fn from_json(value: &Value) -> std::result::Result<RoiRectangle, DecodeError> {
        let obj = parse_object(value)?;
        required(obj, "type", parse_const("rectangle"))?;
        Ok(RoiRectangle {
            x: required(obj, "x", parse_number)?,
            y: required(obj, "y", parse_number)?,
            width: required(obj, "width", parse_number)?,
            height: required(obj, "height", parse_number)?,
            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        put_number(&mut out, "x", self.x);
        put_number(&mut out, "y", self.y);
        put_number(&mut out, "width", self.width);
        put_number(&mut out, "height", self.height);
        out.insert("type".to_string(), Value::from("rectangle"));
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct RoiContourPoint {
    pub x: f64,
    pub y: f64,
    pub raw: Map<String, Value>,
}

impl RoiContourPoint {
    pub fn from_json(value: &Value) -> std::result::Result<RoiContourPoint, DecodeError> {
        let obj = parse_object(value)?;
        Ok(RoiContourPoint {
            x: required(obj, "x", parse_number)?,
            y: required(obj, "y", parse_number)?,
            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        put_number(&mut out, "x", self.x);
        put_number(&mut out, "y", self.y);
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub struct RoiContour {
    pub points: Vec<RoiContourPoint>,
    pub raw: Map<String, Value>,
}

impl RoiContour {
    pub fn from_json(value: &Value) -> std::result::Result<RoiContour, DecodeError> {
        let obj = parse_object(value)?;
        required(obj, "type", parse_const("contour"))?;
        Ok(RoiContour {
            points: required(obj, "points", parse_array(RoiContourPoint::from_json))?,
            raw: obj.clone(),
        })
    }

    pub fn to_json(&self) -> Value {
        let mut out = self.raw.clone();
        out.insert("points".to_string(), Value::Array((&self.points).iter().map(|x| x.to_json()).collect()));
        out.insert("type".to_string(), Value::from("contour"));
        Value::Object(out)
    }
}


#[derive(Debug, Clone, PartialEq)]
pub enum Command {
    SetPop(SetPop),
    Ping(Ping),
    SetSource(SetSource),
    Uploaded(Uploaded),
    StopSource(StopSource),
    GetGraph(GetGraph),
    Quit(Quit),
    Unknown(Map<String, Value>),
}

impl Command {
    pub fn from_json(value: &Value) -> std::result::Result<Command, DecodeError> {
        let obj = parse_object(value)?;
        if obj.get("type").and_then(Value::as_str) == Some("setPop") {
            return Ok(Command::SetPop(SetPop::from_json(value)?));
        }
        if obj.get("type").and_then(Value::as_str) == Some("ping") {
            return Ok(Command::Ping(Ping::from_json(value)?));
        }
        if obj.get("type").and_then(Value::as_str) == Some("setSource") {
            return Ok(Command::SetSource(SetSource::from_json(value)?));
        }
        if obj.get("type").and_then(Value::as_str) == Some("uploaded") {
            return Ok(Command::Uploaded(Uploaded::from_json(value)?));
        }
        if obj.get("type").and_then(Value::as_str) == Some("stopSource") {
            return Ok(Command::StopSource(StopSource::from_json(value)?));
        }
        if obj.get("type").and_then(Value::as_str) == Some("getGraph") {
            return Ok(Command::GetGraph(GetGraph::from_json(value)?));
        }
        if obj.get("type").and_then(Value::as_str) == Some("quit") {
            return Ok(Command::Quit(Quit::from_json(value)?));
        }
        fail("no variant matches".to_string())
    }

    pub fn decode(value: &Value) -> Command {
        if !within(value, MAX_DEPTH) {
            return Command::Unknown(Map::new());
        }
        Command::from_json(value)
            .unwrap_or_else(|_| Command::Unknown(value.as_object().cloned().unwrap_or_default()))
    }

    pub fn to_json(&self) -> Value {
        match self {
            Command::SetPop(v) => v.to_json(),
            Command::Ping(v) => v.to_json(),
            Command::SetSource(v) => v.to_json(),
            Command::Uploaded(v) => v.to_json(),
            Command::StopSource(v) => v.to_json(),
            Command::GetGraph(v) => v.to_json(),
            Command::Quit(v) => v.to_json(),
            Command::Unknown(raw) => Value::Object(raw.clone()),
        }
    }
}


#[derive(Debug, Clone, PartialEq)]
pub enum GroupMember {
    GroupMemberUrl(GroupMemberUrl),
    GroupMemberUpload(GroupMemberUpload),
}

impl GroupMember {
    pub fn from_json(value: &Value) -> std::result::Result<GroupMember, DecodeError> {
        let obj = parse_object(value)?;
        if obj.contains_key("url") {
            exactly_one(obj, &["url", "upload"])?;
            return Ok(GroupMember::GroupMemberUrl(GroupMemberUrl::from_json(value)?));
        }
        if obj.contains_key("upload") {
            exactly_one(obj, &["url", "upload"])?;
            return Ok(GroupMember::GroupMemberUpload(GroupMemberUpload::from_json(value)?));
        }
        fail("no variant matches".to_string())
    }

    pub fn to_json(&self) -> Value {
        match self {
            GroupMember::GroupMemberUrl(v) => v.to_json(),
            GroupMember::GroupMemberUpload(v) => v.to_json(),
        }
    }
}


#[derive(Debug, Clone, PartialEq)]
pub enum JobMessage {
    Start(Start),
    PredictionMessage(PredictionMessage),
    Dropped(Dropped),
    Usage(Usage),
    End(End),
}

impl JobMessage {
    pub fn from_json(value: &Value) -> std::result::Result<JobMessage, DecodeError> {
        let obj = parse_object(value)?;
        if obj.get("type").and_then(Value::as_str) == Some("start") {
            return Ok(JobMessage::Start(Start::from_json(value)?));
        }
        if obj.get("type").and_then(Value::as_str) == Some("prediction") {
            return Ok(JobMessage::PredictionMessage(PredictionMessage::from_json(value)?));
        }
        if obj.get("type").and_then(Value::as_str) == Some("dropped") {
            return Ok(JobMessage::Dropped(Dropped::from_json(value)?));
        }
        if obj.get("type").and_then(Value::as_str) == Some("usage") {
            return Ok(JobMessage::Usage(Usage::from_json(value)?));
        }
        if obj.get("type").and_then(Value::as_str) == Some("end") {
            return Ok(JobMessage::End(End::from_json(value)?));
        }
        fail("no variant matches".to_string())
    }

    pub fn to_json(&self) -> Value {
        match self {
            JobMessage::Start(v) => v.to_json(),
            JobMessage::PredictionMessage(v) => v.to_json(),
            JobMessage::Dropped(v) => v.to_json(),
            JobMessage::Usage(v) => v.to_json(),
            JobMessage::End(v) => v.to_json(),
        }
    }
}


#[derive(Debug, Clone, PartialEq)]
pub enum Message {
    Result(Result),
    Send(Send),
    Credit(Credit),
    Start(Start),
    PredictionMessage(PredictionMessage),
    Dropped(Dropped),
    Usage(Usage),
    End(End),
    Done(Done),
    Pong(Pong),
    ErrorMessage(ErrorMessage),
    Unknown(Map<String, Value>),
}

impl Message {
    pub fn from_json(value: &Value) -> std::result::Result<Message, DecodeError> {
        let obj = parse_object(value)?;
        if obj.get("type").and_then(Value::as_str) == Some("result") {
            return Ok(Message::Result(Result::from_json(value)?));
        }
        if obj.get("type").and_then(Value::as_str) == Some("send") {
            return Ok(Message::Send(Send::from_json(value)?));
        }
        if obj.get("type").and_then(Value::as_str) == Some("credit") {
            return Ok(Message::Credit(Credit::from_json(value)?));
        }
        if obj.get("type").and_then(Value::as_str) == Some("start") {
            return Ok(Message::Start(Start::from_json(value)?));
        }
        if obj.get("type").and_then(Value::as_str) == Some("prediction") {
            return Ok(Message::PredictionMessage(PredictionMessage::from_json(value)?));
        }
        if obj.get("type").and_then(Value::as_str) == Some("dropped") {
            return Ok(Message::Dropped(Dropped::from_json(value)?));
        }
        if obj.get("type").and_then(Value::as_str) == Some("usage") {
            return Ok(Message::Usage(Usage::from_json(value)?));
        }
        if obj.get("type").and_then(Value::as_str) == Some("end") {
            return Ok(Message::End(End::from_json(value)?));
        }
        if obj.get("type").and_then(Value::as_str) == Some("done") {
            return Ok(Message::Done(Done::from_json(value)?));
        }
        if obj.get("type").and_then(Value::as_str) == Some("pong") {
            return Ok(Message::Pong(Pong::from_json(value)?));
        }
        if obj.get("type").and_then(Value::as_str) == Some("error") {
            return Ok(Message::ErrorMessage(ErrorMessage::from_json(value)?));
        }
        fail("no variant matches".to_string())
    }

    pub fn decode(value: &Value) -> Message {
        if !within(value, MAX_DEPTH) {
            return Message::Unknown(Map::new());
        }
        Message::from_json(value)
            .unwrap_or_else(|_| Message::Unknown(value.as_object().cloned().unwrap_or_default()))
    }

    pub fn to_json(&self) -> Value {
        match self {
            Message::Result(v) => v.to_json(),
            Message::Send(v) => v.to_json(),
            Message::Credit(v) => v.to_json(),
            Message::Start(v) => v.to_json(),
            Message::PredictionMessage(v) => v.to_json(),
            Message::Dropped(v) => v.to_json(),
            Message::Usage(v) => v.to_json(),
            Message::End(v) => v.to_json(),
            Message::Done(v) => v.to_json(),
            Message::Pong(v) => v.to_json(),
            Message::ErrorMessage(v) => v.to_json(),
            Message::Unknown(raw) => Value::Object(raw.clone()),
        }
    }
}


#[derive(Debug, Clone, PartialEq)]
pub enum PopComponent {
    InferenceComponent(InferenceComponent),
    RawComponent(RawComponent),
}

impl PopComponent {
    pub fn from_json(value: &Value) -> std::result::Result<PopComponent, DecodeError> {
        let obj = parse_object(value)?;
        if obj.get("type").and_then(Value::as_str) == Some("inference") {
            return Ok(PopComponent::InferenceComponent(InferenceComponent::from_json(value)?));
        }
        return Ok(PopComponent::RawComponent(RawComponent::from_json(value)?));
    }

    pub fn to_json(&self) -> Value {
        match self {
            PopComponent::InferenceComponent(v) => v.to_json(),
            PopComponent::RawComponent(v) => v.to_json(),
        }
    }
}


#[derive(Debug, Clone, PartialEq)]
pub enum Roi {
    RoiRectangle(RoiRectangle),
    RoiContour(RoiContour),
}

impl Roi {
    pub fn from_json(value: &Value) -> std::result::Result<Roi, DecodeError> {
        let obj = parse_object(value)?;
        if obj.get("type").and_then(Value::as_str) == Some("rectangle") {
            return Ok(Roi::RoiRectangle(RoiRectangle::from_json(value)?));
        }
        if obj.get("type").and_then(Value::as_str) == Some("contour") {
            return Ok(Roi::RoiContour(RoiContour::from_json(value)?));
        }
        fail("no variant matches".to_string())
    }

    pub fn to_json(&self) -> Value {
        match self {
            Roi::RoiRectangle(v) => v.to_json(),
            Roi::RoiContour(v) => v.to_json(),
        }
    }
}
