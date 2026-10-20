//! Strict JSON used for the existing on-disk snapshot format and local Qt bridge.
//! No network-fetched dependencies are needed to build this application.
use std::collections::BTreeMap;

#[derive(Clone, Debug, PartialEq)]
pub enum Value {
    Null,
    Bool(bool),
    Number(String),
    String(String),
    Array(Vec<Value>),
    Object(BTreeMap<String, Value>),
}

impl From<&str> for Value { fn from(v: &str) -> Self { Self::String(v.into()) } }
impl From<String> for Value { fn from(v: String) -> Self { Self::String(v) } }
impl From<bool> for Value { fn from(v: bool) -> Self { Self::Bool(v) } }
impl From<u64> for Value { fn from(v: u64) -> Self { Self::Number(v.to_string()) } }
impl From<usize> for Value { fn from(v: usize) -> Self { Self::Number(v.to_string()) } }
impl From<Vec<Value>> for Value { fn from(v: Vec<Value>) -> Self { Self::Array(v) } }

#[macro_export]
macro_rules! obj {
    ($($key:literal => $value:expr),* $(,)?) => {{
        let mut map = std::collections::BTreeMap::new();
        $(map.insert($key.to_string(), $crate::json::Value::from($value));)*
        $crate::json::Value::Object(map)
    }};
}

impl Value {
    pub fn get(&self, key: &str) -> Result<&Self, String> {
        self.opt(key).ok_or_else(|| format!("Missing JSON field: {key}"))
    }
    pub fn opt(&self, key: &str) -> Option<&Self> {
        if let Self::Object(map) = self { map.get(key) } else { None }
    }
    pub fn text(&self) -> Result<&str, String> {
        if let Self::String(value) = self { Ok(value) } else { Err("Expected a JSON string".into()) }
    }
    pub fn array(&self) -> Result<&Vec<Self>, String> {
        if let Self::Array(value) = self { Ok(value) } else { Err("Expected a JSON array".into()) }
    }
    pub fn number(&self) -> Result<u64, String> {
        if let Self::Number(value) = self { value.parse().map_err(|_| "Expected a nonnegative integer".into()) }
        else { Err("Expected a JSON integer".into()) }
    }
    pub fn boolean(&self) -> Result<bool, String> {
        if let Self::Bool(value) = self { Ok(*value) } else { Err("Expected a JSON boolean".into()) }
    }
    pub fn dump(&self) -> String {
        match self {
            Self::Null => "null".into(),
            Self::Bool(v) => v.to_string(),
            Self::Number(v) => v.clone(),
            Self::String(v) => quote(v),
            Self::Array(items) => format!("[{}]", items.iter().map(Self::dump).collect::<Vec<_>>().join(",")),
            Self::Object(items) => format!("{{{}}}", items.iter().map(|(k,v)| format!("{}:{}", quote(k),v.dump())).collect::<Vec<_>>().join(",")),
        }
    }
}

pub fn quote(text: &str) -> String {
    let mut out = String::from("\"");
    for c in text.chars() {
        match c {
            '"' => out.push_str("\\\""), '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"), '\r' => out.push_str("\\r"), '\t' => out.push_str("\\t"),
            c if c < ' ' => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => out.push(c),
        }
    }
    out.push('"'); out
}

pub fn parse(text: &str) -> Result<Value, String> {
    if text.len() > 16 * 1024 * 1024 { return Err("JSON exceeds the 16 MiB limit".into()); }
    let mut p = Parser { bytes: text.as_bytes(), pos: 0 };
    let value = p.value(0)?;
    p.space();
    if p.pos != p.bytes.len() { return Err("Trailing JSON data".into()); }
    Ok(value)
}

struct Parser<'a> { bytes: &'a [u8], pos: usize }
impl Parser<'_> {
    fn space(&mut self) { while self.pos < self.bytes.len() && matches!(self.bytes[self.pos], b' '|b'\t'|b'\n'|b'\r') { self.pos += 1; } }
    fn consume(&mut self, byte: u8) -> bool {
        self.space();
        if self.bytes.get(self.pos) == Some(&byte) { self.pos += 1; true } else { false }
    }
    fn value(&mut self, depth: usize) -> Result<Value, String> {
        if depth > 128 { return Err("JSON nesting limit exceeded".into()); }
        self.space();
        match self.bytes.get(self.pos).copied() {
            Some(b'"') => Ok(Value::String(self.string()?)),
            Some(b'{') => {
                self.pos += 1;
                let mut map = BTreeMap::new();
                if self.consume(b'}') { return Ok(Value::Object(map)); }
                loop {
                    self.space(); let key = self.string()?;
                    if !self.consume(b':') { return Err("Expected ':' in JSON object".into()); }
                    let value = self.value(depth + 1)?;
                    if map.insert(key, value).is_some() { return Err("Duplicate JSON object key".into()); }
                    if self.consume(b'}') { break; }
                    if !self.consume(b',') { return Err("Expected ',' in JSON object".into()); }
                }
                Ok(Value::Object(map))
            }
            Some(b'[') => {
                self.pos += 1; let mut items = vec![];
                if self.consume(b']') { return Ok(Value::Array(items)); }
                loop {
                    items.push(self.value(depth + 1)?);
                    if self.consume(b']') { break; }
                    if !self.consume(b',') { return Err("Expected ',' in JSON array".into()); }
                }
                Ok(Value::Array(items))
            }
            Some(b't') => { self.literal(b"true")?; Ok(Value::Bool(true)) }
            Some(b'f') => { self.literal(b"false")?; Ok(Value::Bool(false)) }
            Some(b'n') => { self.literal(b"null")?; Ok(Value::Null) }
            Some(b'-' | b'0'..=b'9') => self.number(),
            _ => Err("Unexpected JSON token".into()),
        }
    }
    fn literal(&mut self, expected: &[u8]) -> Result<(), String> {
        if self.bytes.get(self.pos..self.pos + expected.len()) != Some(expected) { return Err("Invalid JSON literal".into()); }
        self.pos += expected.len(); Ok(())
    }
    fn hex4(&mut self) -> Result<u32, String> {
        let bytes = self.bytes.get(self.pos..self.pos + 4).ok_or("Incomplete Unicode escape")?;
        let digits = std::str::from_utf8(bytes).map_err(|_| "Invalid Unicode escape")?;
        let number = u32::from_str_radix(digits, 16).map_err(|_| "Invalid Unicode escape")?;
        self.pos += 4; Ok(number)
    }
    fn string(&mut self) -> Result<String, String> {
        if self.bytes.get(self.pos) != Some(&b'"') { return Err("Expected a JSON string".into()); }
        self.pos += 1; let mut out = Vec::new();
        loop {
            let c = *self.bytes.get(self.pos).ok_or("Unterminated JSON string")?; self.pos += 1;
            match c {
                b'"' => return String::from_utf8(out).map_err(|_| "Invalid UTF-8 in JSON string".into()),
                b'\\' => {
                    let escaped = *self.bytes.get(self.pos).ok_or("Incomplete JSON escape")?; self.pos += 1;
                    match escaped {
                        b'"' | b'\\' | b'/' => out.push(escaped), b'b' => out.push(8), b'f' => out.push(12),
                        b'n' => out.push(b'\n'), b'r' => out.push(b'\r'), b't' => out.push(b'\t'),
                        b'u' => {
                            let first = self.hex4()?;
                            let code = if (0xd800..=0xdbff).contains(&first) {
                                if self.bytes.get(self.pos..self.pos + 2) != Some(b"\\u") { return Err("Missing low Unicode surrogate".into()); }
                                self.pos += 2; let low = self.hex4()?;
                                if !(0xdc00..=0xdfff).contains(&low) { return Err("Invalid low Unicode surrogate".into()); }
                                0x10000 + ((first - 0xd800) << 10) + low - 0xdc00
                            } else { first };
                            let c = char::from_u32(code).ok_or("Invalid Unicode code point")?;
                            let mut buf = [0;4]; out.extend_from_slice(c.encode_utf8(&mut buf).as_bytes());
                        }
                        _ => return Err("Invalid JSON escape".into()),
                    }
                }
                0..=31 => return Err("Unescaped control character in JSON".into()),
                _ => out.push(c),
            }
        }
    }
    fn number(&mut self) -> Result<Value, String> {
        let start = self.pos;
        if self.bytes.get(self.pos) == Some(&b'-') { self.pos += 1; }
        match self.bytes.get(self.pos) {
            Some(b'0') => self.pos += 1,
            Some(b'1'..=b'9') => while matches!(self.bytes.get(self.pos), Some(b'0'..=b'9')) { self.pos += 1; },
            _ => return Err("Invalid JSON number".into()),
        }
        if self.bytes.get(self.pos) == Some(&b'.') {
            self.pos += 1; let begin = self.pos;
            while matches!(self.bytes.get(self.pos), Some(b'0'..=b'9')) { self.pos += 1; }
            if begin == self.pos { return Err("Invalid JSON fraction".into()); }
        }
        if matches!(self.bytes.get(self.pos), Some(b'e'|b'E')) {
            self.pos += 1;
            if matches!(self.bytes.get(self.pos), Some(b'+'|b'-')) { self.pos += 1; }
            let begin = self.pos;
            while matches!(self.bytes.get(self.pos), Some(b'0'..=b'9')) { self.pos += 1; }
            if begin == self.pos { return Err("Invalid JSON exponent".into()); }
        }
        Ok(Value::Number(std::str::from_utf8(&self.bytes[start..self.pos]).unwrap().into()))
    }
}

#[cfg(test)] mod tests {
    use super::*;
    #[test] fn unicode_round_trip() {
        let value = parse(r#"{"mask":"\ud83d\udc79","name":"卍解","n":18446744073709551615}"#).unwrap();
        assert_eq!(value.get("mask").unwrap().text().unwrap(), "👹");
        assert_eq!(parse(&value.dump()).unwrap(), value);
    }
    #[test] fn reject_malformed() {
        for value in ["01", "[1,]", "{\"a\":1,\"a\":2}", "\"\\ud800\"", "1e", "true false", "\"\n\""] {
            assert!(parse(value).is_err(), "{value}");
        }
    }
}
