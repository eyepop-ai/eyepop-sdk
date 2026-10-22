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
}
