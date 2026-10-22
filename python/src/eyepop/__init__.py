from importlib.metadata import version as _dist_version


def version() -> str:
    return _dist_version("eyepop")
