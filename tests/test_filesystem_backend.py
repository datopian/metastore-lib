"""Tests for the filysystem based storage backend
"""
from typing import Any, Dict

import pytest

from metastore.backend.filesystem import FilesystemStorage, exc


def create_test_datapackage(name, **kwargs):
    # type: (str, ...) -> Dict[str, Any]
    """Create a datapackage.json structure for testing purposes
    """
    package = {"name": name,
               "resources": [
                   {"path": "data/myresource.csv"}
               ]}
    package.update(kwargs)
    return package


def test_datapackage_create_fetch():
    backend = FilesystemStorage('mem://')
    p1_info = backend.create('myorg/mydataset', create_test_datapackage('mydataset'))
    assert p1_info.package_id == 'myorg/mydataset'
    assert p1_info.revision is not None
    assert p1_info.package['resources'][0]['path'] == 'data/myresource.csv'

    p2_info = backend.fetch('myorg/mydataset')
    assert p1_info.package == p2_info.package


def test_datapackage_create_name_conflict():
    backend = FilesystemStorage('mem://')
    package_info = backend.create('myorg/mydataset', create_test_datapackage('mydataset'))
    assert package_info.package_id == 'myorg/mydataset'

    with pytest.raises(exc.Conflict):
        backend.create('myorg/mydataset', create_test_datapackage('mydataset'))


def test_datapackage_fetch_not_found():
    backend = FilesystemStorage('mem://')
    with pytest.raises(exc.NotFound):
        backend.fetch('myorg/mydataset')


def test_datapackage_update_partial():
    backend = FilesystemStorage('mem://')
    rev1_info = backend.create('myorg/mydataset', create_test_datapackage('mydataset'))
    rev2_info = backend.update('myorg/mydataset', {"type": "csv"}, partial=True)
    assert rev1_info.package_id == rev2_info.package_id
    assert rev1_info.revision != rev2_info.revision

    package_info = backend.fetch('myorg/mydataset')
    assert package_info.revision == rev2_info.revision
    assert package_info.package['type'] == 'csv'
    assert package_info.package['name'] == 'mydataset'


def test_datapackage_update_full():
    backend = FilesystemStorage('mem://')
    backend.create('myorg/mydataset', create_test_datapackage('mydataset', type='xls'))
    backend.update('myorg/mydataset', {"name": "my-data-set"})

    package_info = backend.fetch('myorg/mydataset')
    assert package_info.package['name'] == 'my-data-set'
    assert 'type' not in package_info.package


def test_datapackage_fetch_revision():
    backend = FilesystemStorage('mem://')
    rev1_info = backend.create('myorg/mydataset', create_test_datapackage('mydataset'))
    backend.update('myorg/mydataset', {"type": "csv"}, partial=True)

    pkg_info = backend.fetch('myorg/mydataset', revision_ref=rev1_info.revision)
    assert pkg_info.revision == rev1_info.revision
    assert 'type' not in pkg_info.package


def test_datapackage_delete():
    backend = FilesystemStorage('mem://')
    package_info = backend.create('myorg/mydataset', create_test_datapackage('mydataset'))
    assert package_info.package_id == 'myorg/mydataset'

    backend.delete(package_info.package_id)
    with pytest.raises(exc.NotFound):
        backend.fetch('myorg/mydataset')


def test_datapackage_delete_non_existing():
    backend = FilesystemStorage('mem://')
    with pytest.raises(exc.NotFound):
        backend.delete('myorg/someid')


def test_revision_list_one_revision():
    backend = FilesystemStorage('mem://')
    p1 = backend.create('myorg/mydataset', create_test_datapackage('mydataset'))
    revs = backend.revision_list('myorg/mydataset')
    assert len(revs) == 1
    assert revs[0].revision == p1.revision


def test_revision_list_multiple_revisions():
    backend = FilesystemStorage('mem://')
    p1 = backend.create('myorg/mydataset', create_test_datapackage('mydataset'))
    p2 = backend.update('myorg/mydataset', {"type": "csv"}, partial=True, update_description="Set type to csv")
    p3 = backend.update('myorg/mydataset', {"type": "xls"}, partial=True, update_description="Set type to xls")

    revs = backend.revision_list('myorg/mydataset')
    assert len(revs) == 3
    assert revs[2].revision == p1.revision
    assert revs[1].revision == p2.revision
    assert revs[1].description == "Set type to csv"
    assert revs[0].revision == p3.revision
    assert revs[0].description == "Set type to xls"


def test_revision_list_multiple_revisions_different_packages():
    backend = FilesystemStorage('mem://')
    p1 = backend.create('myorg/mydataset', create_test_datapackage('mydataset'))
    p2 = backend.create('myorg/otherdataset', create_test_datapackage('otherdataset'))
    p3 = backend.update('myorg/mydataset', {"type": "csv"}, partial=True, update_description="Set type to csv")
    p4 = backend.update('myorg/otherdataset', {"type": "xls"}, partial=True, update_description="Set type to xls")

    revs = backend.revision_list('myorg/mydataset')
    assert len(revs) == 2
    assert revs[1].revision == p1.revision
    assert revs[0].revision == p3.revision
    assert revs[0].description == "Set type to csv"

    revs = backend.revision_list('myorg/otherdataset')
    assert len(revs) == 2
    assert revs[1].revision == p2.revision
    assert revs[0].revision == p4.revision
    assert revs[0].description == "Set type to xls"


def test_revision_fetch():
    backend = FilesystemStorage('mem://')
    backend.create('myorg/mydataset', create_test_datapackage('mydataset'))
    p2 = backend.update('myorg/mydataset', {"type": "csv"}, partial=True, update_description="Set type to csv")

    rev = backend.revision_fetch(p2.package_id, p2.revision)
    assert p2.revision == rev.revision
    assert "Set type to csv" == rev.description


def test_revision_fetch_no_package():
    backend = FilesystemStorage('mem://')
    with pytest.raises(exc.NotFound):
        backend.revision_fetch('myorg/mydataset', '123123123123123')


def test_revision_fetch_no_revision():
    backend = FilesystemStorage('mem://')
    p1 = backend.create('myorg/mydataset', create_test_datapackage('mydataset'))
    rev = backend.revision_fetch(p1.package_id, p1.revision)
    assert p1.revision == rev.revision
    with pytest.raises(exc.NotFound):
        backend.revision_fetch(p1.package_id, '123123123123123123')


def test_tag_create_fetch():
    backend = FilesystemStorage('mem://')
    p1 = backend.create('myorg/mydataset', create_test_datapackage('mydataset'))
    r1 = backend.tag_create(p1.package_id, p1.revision, 'version-1.0', "My nice little tag")
    t1 = backend.tag_fetch(p1.package_id, 'version-1.0')
    assert t1.revision == r1.revision
    assert t1.name == 'version-1.0'


@pytest.mark.parametrize('name', [
    'with space',
    'with,comma',
    'with!',
    'with\n',
    '',
    'foo\tbar',
])
def test_tag_create_invalid_names(name):
    backend = FilesystemStorage('mem://')
    p1 = backend.create('myorg/mydataset', create_test_datapackage('mydataset'))
    with pytest.raises(ValueError):
        backend.tag_create(p1.package_id, p1.revision, name, description="Invalid tag name")


def test_tag_fetch_no_tag():
    backend = FilesystemStorage('mem://')
    p1 = backend.create('myorg/mydataset', create_test_datapackage('mydataset'))
    with pytest.raises(exc.NotFound):
        backend.tag_fetch(p1.package_id, 'version-1.0')


def test_tag_fetch_no_package():
    backend = FilesystemStorage('mem://')
    p1 = backend.create('myorg/mydataset', create_test_datapackage('mydataset'))
    backend.tag_create(p1.package_id, p1.revision, 'version-1.0', "My nice little tag")
    with pytest.raises(exc.NotFound):
        backend.tag_fetch('myorg/otherpackage', 'version-1.0')


def test_tag_list():
    backend = FilesystemStorage('mem://')
    p1 = backend.create('myorg/mydataset', create_test_datapackage('mydataset'))
    backend.tag_create(p1.package_id, p1.revision, 'version-1.0', "First version")
    p2 = backend.update('myorg/mydataset', create_test_datapackage('mydataset', type='csv'))
    backend.tag_create(p1.package_id, p2.revision, 'version-1.1', "Second version")
    p3 = backend.create('myorg/ohterdataset', create_test_datapackage('otherdataset'))
    backend.tag_create(p3.package_id, p3.revision, 'version-1.0', "First version")

    tags = backend.tag_list('myorg/mydataset')
    assert len(tags) == 2
    assert tags[0].name == 'version-1.0'
    assert tags[0].revision_ref == p1.revision
    assert tags[1].name == 'version-1.1'
    assert tags[1].revision_ref == p2.revision


def test_tag_list_no_tags():
    backend = FilesystemStorage('mem://')
    p1 = backend.create('myorg/mydataset', create_test_datapackage('mydataset'))
    backend.tag_create(p1.package_id, p1.revision, 'version-1.0', "First version")
    backend.create('myorg/otherdataset', create_test_datapackage('otherdataset'))

    tags = backend.tag_list('myorg/otherdataset')
    assert 0 == len(tags)


def test_tag_list_no_package():
    backend = FilesystemStorage('mem://')
    with pytest.raises(exc.NotFound):
        backend.tag_list('myorg/otherdataset')
