"""Data classes for packages & related models
"""
from datetime import datetime
from typing import Any, Dict, Optional

# Python type definition for datapackage.json dicts
# This may be further specified in the future (esp. if Python 2.x support is dropped)
DataPackageType = Dict[str, Any]


class PackageRevisionInfo(object):
    """Revision information
    """
    package_id = None  # type: str
    revision = None  # type: str
    created = None  # type: datetime
    description = None  # type: Optional[str]
    package = None  # type: Optional[DataPackageType]

    def __init__(self, package_id, revision, created, description=None, package=None):
        self.package_id = package_id
        self.revision = revision
        self.created = created
        self.description = description
        self.package = package

    def __eq__(self, other):
        if isinstance(self, other.__class__):
            return self.package_id == other.package_id and self.revision == other.revision
        return False


class TagInfo(object):
    """Tag information
    """
    package_id = None  # type: str
    name = None  # type: str
    created = None  # type: datetime
    revision_ref = None  # type: str
    revision = None  # type: Optional[PackageRevisionInfo]
    description = None  # type: Optional[str]

    def __init__(self, package_id, name, created, revision_ref, revision=None, description=None):
        self.package_id = package_id
        self.name = name
        self.created = created
        self.revision_ref = revision_ref
        self.revision = revision
        self.description = description

    def __eq__(self, other):
        if isinstance(self, other.__class__):
            return self.package_id == other.package_id and self.name == other.name
        return False
