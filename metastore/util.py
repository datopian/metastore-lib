import importlib
from typing import Callable, Optional


def get_callable(callable_str, base_package=None):
    # type: (str, Optional[str]) -> Callable
    """Get a callable function / class constructor from a string of the form
    `package.subpackage.module:callable`

    >>> type(get_callable('os.path:basename')).__name__
    'function'

    >>> type(get_callable('basename', 'os.path')).__name__
    'function'
    """
    if ':' in callable_str:
        module_name, callable_name = callable_str.split(':', 1)
        module = importlib.import_module(module_name, base_package)
    elif base_package:
        module = importlib.import_module(base_package)
        callable_name = callable_str
    else:
        raise ValueError("Expecting base_package to be set if only class name is provided")

    return getattr(module, callable_name)  # type: ignore


def is_hex_str(value, chars=40):
    # type: (str, int) -> bool
    """Check if a string is a hex-only string of exactly :param:`chars` characters length.

    This is useful to verify that a string contains a valid SHA, MD5 or UUID-like value.

    >>> is_hex_str('0f1128046248f83dc9b9ab187e16fad0ff596128f1524d05a9a77c4ad932f10a', 64)
    True

    >>> is_hex_str('0f1128046248f83dc9b9ab187e16fad0ff596128f1524d05a9a77c4ad932f10a', 32)
    False

    >>> is_hex_str('0f1128046248f83dc9b9ab187e1xfad0ff596128f1524d05a9a77c4ad932f10a', 64)
    False

    >>> is_hex_str('ef42bab1191da272f13935f78c401e3de0c11afb')
    True

    >>> is_hex_str('ef42bab1191da272f13935f78c401e3de0c11afb'.upper())
    True

    >>> is_hex_str('ef42bab1191da272f13935f78c401e3de0c11afb', 64)
    False

    >>> is_hex_str('ef42bab1191da272f13935.78c401e3de0c11afb')
    False
    """
    if len(value) != chars:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True
