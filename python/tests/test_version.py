from importlib.metadata import requires, version

import eyepop


def test_version_matches_distribution():
    assert eyepop.version() == version("eyepop")


def test_no_required_dependencies():
    assert not requires("eyepop")
