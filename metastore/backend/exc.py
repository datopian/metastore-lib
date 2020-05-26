"""Storage backend exceptions
"""


class StorageBackendError(RuntimeError):
    """Base exception for all storage backend errors
    """
    pass


class Conflict(StorageBackendError):
    """An error representing a conflict between objects

    This may be raised, for example, when trying to modify a package
    which has already been modified in some other manner, or when trying
    to create a package with an ID that already exists.
    """
    pass


class NotFound(StorageBackendError):
    """An error that indicates the user is trying to access an object which
    does not exist or has been deleted from storage
    """
    pass
