"""Backend namespace
"""
from typing import Any, Dict, List, Optional

from metastore.types import Author, DataPackageType, PackageRevisionInfo, TagInfo
from metastore.util import get_callable

BACKEND_CLASSES = {'github': 'metastore.backend.github:GitHubStorage',
                   'filesystem': 'metastore.backend.filesystem:FilesystemStorage'}


class StorageBackend(object):
    """Abstract interface for storage backend classes
    """
    def create(self, package_id, metadata, author=None, message=None):
        # type: (str, DataPackageType, Optional[Author], Optional[str]) -> PackageRevisionInfo
        """Create a new data package
        """
        raise NotImplementedError("This method is not implemented for this backend")

    def fetch(self, package_id, revision_ref=None):
        # type: (str, Optional[str]) -> PackageRevisionInfo
        """Fetch a data package, potentially at a given revision / tag

        :raises metastore.backend.exc.NotFound: Raised if the package or referenced revision do not exist
        """
        raise NotImplementedError("This method is not implemented for this backend")

    def update(self, package_id, metadata, author=None, partial=False, message=None, base_revision_ref=None):
        # type: (str, DataPackageType, Optional[Author], bool, Optional[str], Optional[str]) -> PackageRevisionInfo
        """Update or partial update (patch) a data package
        """
        raise NotImplementedError("This method is not implemented for this backend")

    def delete(self, package_id):
        # type: (str) -> None
        """Delete a data package

        :raises metastore.backend.exc.NotFound: Raised if the package does not exist
        """
        raise NotImplementedError("This method is not implemented for this backend")

    def revision_list(self, package_id):
        # type: (str) -> List[PackageRevisionInfo]
        """Get list of revisions for a data package

        Note that when listing, :attr:`metastore.types.PackageRevisionInfo.package`
        will not be set in the return value. If you need to access the actual package
        metadata and not just revision information, fetch the package data by calling
        :meth:`fetch`.

        :raises metastore.backend.exc.NotFound: Raised if the package does not exist
        """
        raise NotImplementedError("This method is not implemented for this backend")

    def revision_fetch(self, package_id, revision_ref):
        # type: (str, str) -> PackageRevisionInfo
        """Get info about a specific revision of a data package

        NOTE: this does not fetch the data package metadata itself, just info about a revision of it

        :raises metastore.backend.exc.NotFound: Raised if the package or revision do not exist
        """
        raise NotImplementedError("This method is not implemented for this backend")

    def tag_create(self, package_id, revision_ref, name, author=None, description=None):
        # type: (str, str, str, Optional[Author], Optional[str]) -> TagInfo
        """Create a tag (named reference to a revision of a data package)

        :raises metastore.backend.exc.NotFound: Raised if the package or referenced revision do not exist
        """
        raise NotImplementedError("This method is not implemented for this backend")

    def tag_list(self, package_id):
        # type: (str) -> List[TagInfo]
        """Get list of tags for a package

        :raises metastore.backend.exc.NotFound: Raised if the package does not exist
        """
        raise NotImplementedError("This method is not implemented for this backend")

    def tag_fetch(self, package_id, tag):
        # type: (str, str) -> TagInfo
        """Get info about a specific tag of a data package

        NOTE: this does not fetch the data package metadata itself, just info about a revision of it

        :raises metastore.backend.exc.NotFound: Raised if the package or tag do not exist
        """
        raise NotImplementedError("This method is not implemented for this backend")

    def tag_update(self, package_id, tag, author=None, new_name=None, new_description=None):
        # type: (str, str, Optional[Author], Optional[str], Optional[str]) -> TagInfo
        """Modify existing tag name or description

        :raises metastore.backend.exc.NotFound: Raised if the package or tag do not exist
        :raises metastore.backend.exc.Conflict: Raised if the tag name is already in use by another tag
        """
        raise NotImplementedError("This method is not implemented for this backend")

    def tag_delete(self, package_id, tag):
        # type: (str, str) -> None
        """Delete an existing

        :raises metastore.backend.exc.NotFound: Raised if the package or tag do not exist
        """
        raise NotImplementedError("This method is not implemented for this backend")


def create_metastore(backend_type, options):
    # type: (str, Dict[str, Any]) -> StorageBackend
    """Factory for storage backends

    Note that this will import the right backend module only as needed
    """
    if ':' not in backend_type:
        try:
            backend_type = BACKEND_CLASSES[backend_type]
        except KeyError:
            raise ValueError("Unknown backend type: {}".format(type))

    backend = get_callable(backend_type)
    return backend(**options)  # type: ignore
