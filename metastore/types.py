"""Data classes for packages & related models
"""
from datetime import datetime
from typing import Any, Dict, Optional

# Python type definition for datapackage.json dicts
# This may be further specified in the future (esp. if Python 2.x support is dropped)
DataPackageType = Dict[str, Any]


# Data classes. If this was Python 3.7+, we could have used dataclasses here ;)
class Author(object):
    """Revision / tag author information
    """
    name = None  # type: Optional[str]
    email = None  # type: Optional[str]

    def __init__(self, name=None, email=None):
        self.name = name
        self.email = email

    def __eq__(self, other):
        return _compare_attributes(self, other, ('name', 'email'))

    def __repr__(self):
        return '<Author {}>'.format(self.email)


class PackageRevisionInfo(object):
    """Revision information
    """
    package_id = None  # type: str
    revision = None  # type: str
    created = None  # type: datetime
    author = None  # type: Optional[Author]
    description = None  # type: Optional[str]
    package = None  # type: Optional[DataPackageType]

    def __init__(self, package_id, revision, created, author=None, description=None, package=None):
        self.package_id = package_id
        self.revision = revision
        self.created = created
        self.author = author
        self.description = description
        self.package = package

    def __eq__(self, other):
        return _compare_attributes(self, other, ('package_id', 'revision'))


class TagInfo(object):
    """Tag information
    """
    package_id = None  # type: str
    name = None  # type: str
    created = None  # type: datetime
    revision_ref = None  # type: str
    author = None  # type: Optional[Author]
    revision = None  # type: Optional[PackageRevisionInfo]
    description = None  # type: Optional[str]

    def __init__(self, package_id, name, created, revision_ref, author=None, revision=None, description=None):
        self.package_id = package_id
        self.name = name
        self.created = created
        self.revision_ref = revision_ref
        self.author = author
        self.revision = revision
        self.description = description

    def __eq__(self, other):
        return _compare_attributes(self, other, ('package_id', 'name'))


def _compare_attributes(obj, other, key_attributes):
    """Object comparison helper
    """
    if not isinstance(obj, other.__class__):
        return NotImplemented

    try:
        return all(getattr(obj, a) == getattr(obj, a) for a in key_attributes)
    except AttributeError:
        return False
