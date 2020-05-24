"""Backend namespace
"""
from importlib import import_module
from typing import Any, Dict

BACKEND_CLASSES = {'github': 'metastore.backend.gh:GitHubStorage'}


class StorageBackend(object):
    """Abstract interface for storage backend classes
    """
    pass


def create_metastore(backend_type, options):
    # type: (str, Dict[str, Any]) -> StorageBackend
    """Factory for storage backends

    Note that this will import the right backend module only as needed
    """
    # TODO: use importlib and our BACKEND_CLASSES dict, it's nicer

    if backend_type == 'github':
        from .gh import GitHubStorage
        return GitHubStorage(**options)
    else:
        raise ValueError("Unknown backend type: {}".format(type))
