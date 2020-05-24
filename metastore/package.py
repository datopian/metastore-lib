"""Data classes for packages & related models
"""
from typing import Any, Dict, Optional


class PackageInfo(object):
    """Package (dataset) information
    """
    id = None  # type: str
    revision = None  # type: str
    tag = None  # type: Optional[str]
    package = None  # type: Optional[Dict[str, Any]]

    def __init__(self, id, revision, package, tag=None):
        self.id = id
        self.revision = revision
        self.package = package
        self.tag = tag
