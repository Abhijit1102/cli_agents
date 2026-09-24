from .. import constants

def should_ignore(name: str, *, is_dir: bool = False) -> bool:
    if name.startswith(constants.IGNORE_PREFIXES):
        return True
    if is_dir:
        return name in constants.IGNORE_DIRS
    return name in constants.IGNORE_FILES or name.endswith(constants.IGNORE_SUFFIXES)
