#[rustfmt::skip]
pub mod protocol;

/// Version of this SDK, stamped from the release tag.
pub fn version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}

#[cfg(test)]
mod tests {
    #[test]
    fn version_is_package_version() {
        assert!(!super::version().is_empty());
        assert_eq!(super::version(), env!("CARGO_PKG_VERSION"));
    }

    #[test]
    fn a_string_length_counts_code_points() {
        let lengths = [
            crate::protocol::length(&"\u{1F600}".to_string()),
            crate::protocol::length(&"e\u{301}".to_string()),
        ];
        assert_eq!(lengths, [1.0, 2.0]);
    }
}
