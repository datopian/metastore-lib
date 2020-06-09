from typing import Any, Dict

import pytest

from metastore.backend.filesystem import exc
from metastore.types import Author


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


class CommonBackendTestSuite(object):

    ID_PREFIX = 'myorg/'

    @classmethod
    def dataset_id(cls, name):
        return '{}{}'.format(cls.ID_PREFIX, name)

    def test_datapackage_create_fetch(self, backend):
        p1_info = backend.create(self.dataset_id('mydataset'), create_test_datapackage('mydataset'))

        assert p1_info.package_id == self.dataset_id('mydataset')
        assert p1_info.revision is not None
        assert p1_info.package['resources'][0]['path'] == 'data/myresource.csv'

        p2_info = backend.fetch(self.dataset_id('mydataset'))
        assert p1_info.package == p2_info.package

    def test_datapackage_create_name_conflict(self, backend):
        package_info = backend.create(self.dataset_id('mydataset'), create_test_datapackage('mydataset'))
        assert package_info.package_id == self.dataset_id('mydataset')

        with pytest.raises(exc.Conflict):
            backend.create(self.dataset_id('mydataset'), create_test_datapackage('mydataset'))

    def test_datapackage_fetch_not_found(self, backend):
        with pytest.raises(exc.NotFound):
            backend.fetch(self.dataset_id('mydataset'))

    def test_datapackage_update_partial(self, backend):
        rev1_info = backend.create(self.dataset_id('mydataset'), create_test_datapackage('mydataset'))
        rev2_info = backend.update(self.dataset_id('mydataset'), {"type": "csv"}, partial=True)
        assert rev1_info.package_id == rev2_info.package_id
        assert rev1_info.revision != rev2_info.revision

        package_info = backend.fetch(self.dataset_id('mydataset'))
        assert package_info.revision == rev2_info.revision
        assert package_info.package['type'] == 'csv'
        assert package_info.package['name'] == 'mydataset'

    def test_datapackage_update_full(self, backend):
        backend.create(self.dataset_id('mydataset'), create_test_datapackage('mydataset', type='xls'))
        backend.update(self.dataset_id('mydataset'), {"name": "my-data-set"})

        package_info = backend.fetch(self.dataset_id('mydataset'))
        assert package_info.package['name'] == 'my-data-set'
        assert 'type' not in package_info.package

    def test_datapackage_fetch_revision(self, backend):
        pkg = backend.create(self.dataset_id('mydataset'), create_test_datapackage('mydataset'))
        r1 = backend.update(pkg.package_id, {"type": "csv"}, partial=True)
        backend.update(pkg.package_id, {"author": "jimbob@example.com"}, partial=True)

        pkg_info = backend.fetch(pkg.package_id, revision_ref=r1.revision)
        assert pkg_info.revision == r1.revision
        assert 'author' not in pkg_info.package
        assert 'type' in pkg_info.package

    def test_datapackage_delete(self, backend):
        package_info = backend.create(self.dataset_id('mydataset'), create_test_datapackage('mydataset'))
        assert package_info.package_id == self.dataset_id('mydataset')

        backend.delete(package_info.package_id)
        with pytest.raises(exc.NotFound):
            backend.fetch(self.dataset_id('mydataset'))

    def test_datapackage_delete_non_existing(self, backend):
        with pytest.raises(exc.NotFound):
            backend.delete(self.dataset_id('someid'))

    def test_revision_list_one_revision(self, backend):
        p1 = backend.create(self.dataset_id('mydataset'), create_test_datapackage('mydataset'))
        revs = backend.revision_list(self.dataset_id('mydataset'))
        assert len(revs) == 1
        assert revs[0].revision == p1.revision

    def test_revision_list_multiple_revisions(self, backend):
        p1 = backend.create(self.dataset_id('mydataset'), create_test_datapackage('mydataset'))
        p2 = backend.update(self.dataset_id('mydataset'), {"type": "csv"}, partial=True,
                            message="Set type to csv")
        p3 = backend.update(self.dataset_id('mydataset'), {"type": "xls"}, partial=True,
                            message="Set type to xls")

        revs = backend.revision_list(self.dataset_id('mydataset'))
        assert len(revs) == 3
        assert revs[2].revision == p1.revision
        assert revs[1].revision == p2.revision
        assert revs[1].description == "Set type to csv"
        assert revs[0].revision == p3.revision
        assert revs[0].description == "Set type to xls"

    def test_revision_list_multiple_revisions_different_packages(self, backend):
        p1 = backend.create(self.dataset_id('mydataset'), create_test_datapackage('mydataset'))
        p2 = backend.create(self.dataset_id('otherdataset'), create_test_datapackage('otherdataset'))
        p3 = backend.update(self.dataset_id('mydataset'), {"type": "csv"}, partial=True,
                            message="Set type to csv")
        p4 = backend.update(self.dataset_id('otherdataset'), {"type": "xls"}, partial=True,
                            message="Set type to xls")

        revs = backend.revision_list(self.dataset_id('mydataset'))
        assert len(revs) == 2
        assert revs[1].revision == p1.revision
        assert revs[0].revision == p3.revision
        assert revs[0].description == "Set type to csv"

        revs = backend.revision_list(self.dataset_id('otherdataset'))
        assert len(revs) == 2
        assert revs[1].revision == p2.revision
        assert revs[0].revision == p4.revision
        assert revs[0].description == "Set type to xls"

    def test_revision_fetch(self, backend):
        backend.create(self.dataset_id('mydataset'), create_test_datapackage('mydataset'))
        p2 = backend.update(self.dataset_id('mydataset'), {"type": "csv"}, partial=True,
                            message="Set type to csv")

        rev = backend.revision_fetch(p2.package_id, p2.revision)
        assert p2.revision == rev.revision
        assert "Set type to csv" == rev.description

    def test_revision_fetch_no_package(self, backend):
        with pytest.raises(exc.NotFound):
            backend.revision_fetch(self.dataset_id('mydataset'), '123123123123123')

    def test_revision_fetch_no_revision(self, backend):
        p1 = backend.create(self.dataset_id('mydataset'), create_test_datapackage('mydataset'))
        rev = backend.revision_fetch(p1.package_id, p1.revision)
        assert p1.revision == rev.revision
        with pytest.raises(exc.NotFound):
            backend.revision_fetch(p1.package_id, '123123123123123123')

    def test_revision_list_multiple_authors(self, backend):
        author1 = Author(name='Bob Example', email='bob@example.com')
        author2 = Author(name='Bilbo Baggins', email='bilbo@shire.net')
        backend.create(self.dataset_id('mydataset'), create_test_datapackage('mydataset'), author=author1)
        backend.update(self.dataset_id('mydataset'), {"type": "csv"}, partial=True, author=author2,
                       message="Set type to csv")
        backend.update(self.dataset_id('mydataset'), {"type": "xls"}, partial=True, author=author1,
                       message="Set type to xls")

        revs = backend.revision_list(self.dataset_id('mydataset'))
        assert len(revs) == 3
        assert revs[2].author == author1
        assert revs[1].author == author2
        assert revs[0].author == author1
        assert revs[0].author.email == 'bob@example.com'
        assert revs[0].author.name == 'Bob Example'

    def test_tag_create_fetch(self, backend):
        p1 = backend.create(self.dataset_id('mydataset'), create_test_datapackage('mydataset'))
        t1 = backend.tag_create(p1.package_id, p1.revision, 'version-1.0', description='My nice little tag')
        t2 = backend.tag_fetch(p1.package_id, 'version-1.0')
        assert t2.revision == t1.revision
        assert t2.name == 'version-1.0'
        assert t2.description == 'My nice little tag'

    @pytest.mark.parametrize('name', [
        'with space',
        'with!',
        'with\n',
        '',
        'foo\tbar',
    ])
    def test_tag_create_invalid_names(self, name, backend):
        p1 = backend.create(self.dataset_id('mydataset'), create_test_datapackage('mydataset'))
        with pytest.raises(ValueError):
            backend.tag_create(p1.package_id, p1.revision, name, description="Invalid tag name")

    def test_tag_create_fetch_substring_names(self, backend):
        p1 = backend.create(self.dataset_id('mydataset'), create_test_datapackage('mydataset'))
        r1 = backend.tag_create(p1.package_id, p1.revision, 'version-1.0', description="My nice little tag")
        r2 = backend.tag_create(p1.package_id, p1.revision, 'version-1.0.0', description="This is a different tag")
        t1 = backend.tag_fetch(p1.package_id, 'version-1.0')
        assert t1.revision == r1.revision
        assert t1.name == 'version-1.0'
        t2 = backend.tag_fetch(p1.package_id, 'version-1.0.0')
        assert t2.revision == r2.revision
        assert t2.name == 'version-1.0.0'

    def test_tag_create_existing_name(self, backend):
        p1 = backend.create(self.dataset_id('mydataset'), create_test_datapackage('mydataset'))
        backend.tag_create(p1.package_id, p1.revision, 'version-1.0', description="My nice little tag")
        p2 = backend.update(self.dataset_id('mydataset'), create_test_datapackage('mydataset', type='csv'))
        with pytest.raises(exc.Conflict):
            backend.tag_create(p1.package_id, p2.revision, 'version-1.0', description="Next Tag with Same Name")

    def test_tag_fetch_no_tag(self, backend):
        p1 = backend.create(self.dataset_id('mydataset'), create_test_datapackage('mydataset'))
        with pytest.raises(exc.NotFound):
            backend.tag_fetch(p1.package_id, 'version-1.0')

    def test_tag_fetch_no_package(self, backend):
        p1 = backend.create(self.dataset_id('mydataset'), create_test_datapackage('mydataset'))
        backend.tag_create(p1.package_id, p1.revision, 'version-1.0', description="My nice little tag")
        with pytest.raises(exc.NotFound):
            backend.tag_fetch(self.dataset_id('otherdataset'), 'version-1.0')

    def test_tag_list(self, backend):
        p1 = backend.create(self.dataset_id('mydataset'), create_test_datapackage('mydataset'))
        backend.tag_create(p1.package_id, p1.revision, 'version-1.0', description="First version")
        p2 = backend.update(self.dataset_id('mydataset'), create_test_datapackage('mydataset', type='csv'))
        backend.tag_create(p1.package_id, p2.revision, 'version-1.1', description="Second version")
        p3 = backend.create(self.dataset_id('otherdataset'), create_test_datapackage('otherdataset'))
        backend.tag_create(p3.package_id, p3.revision, 'version-1.0', description="First version")

        tags = backend.tag_list(self.dataset_id('mydataset'))
        assert len(tags) == 2
        assert tags[0].name == 'version-1.0'
        assert tags[0].revision_ref == p1.revision
        assert tags[1].name == 'version-1.1'
        assert tags[1].revision_ref == p2.revision

    def test_tag_list_no_tags(self, backend):
        p1 = backend.create(self.dataset_id('mydataset'), create_test_datapackage('mydataset'))
        backend.tag_create(p1.package_id, p1.revision, 'version-1.0', description="First version")
        backend.create(self.dataset_id('otherdataset'), create_test_datapackage('otherdataset'))

        tags = backend.tag_list(self.dataset_id('otherdataset'))
        assert 0 == len(tags)

    def test_tag_list_no_package(self, backend):
        with pytest.raises(exc.NotFound):
            backend.tag_list(self.dataset_id('otherdataset'))

    def test_tag_list_authors(self, backend):
        author1 = Author(name='Bob Example', email='bob@example.com')
        author2 = Author(name='Bilbo Baggins', email='bilbo@shire.net')
        author3 = Author(name='Frodo Baggins', email='frodo@shire.net')
        p1 = backend.create(self.dataset_id('mydataset'), create_test_datapackage('mydataset'), author=author1)
        backend.tag_create(p1.package_id, p1.revision, 'version-1.0', description="First version", author=author2)
        p2 = backend.update(self.dataset_id('mydataset'), create_test_datapackage('mydataset', type='csv'),
                            author=author1)
        backend.tag_create(p1.package_id, p2.revision, 'version-1.1', description="Second version", author=author3)

        tags = backend.tag_list(self.dataset_id('mydataset'))
        assert len(tags) == 2
        assert tags[0].author == author2
        assert tags[1].author == author3
        assert tags[1].author.email == 'frodo@shire.net'
        assert tags[1].author.name == 'Frodo Baggins'

    def test_tag_update(self, backend):
        p1 = backend.create(self.dataset_id('mydataset'), create_test_datapackage('mydataset'))
        t1 = backend.tag_create(p1.package_id, p1.revision, 'version-1.0', description="My nice little tag")
        t2 = backend.tag_update(p1.package_id, t1.name, new_name='v-1.0', new_description='My newer better tag')

        with pytest.raises(exc.NotFound):
            backend.fetch(p1.package_id, revision_ref=t1.name)

        p2 = backend.fetch(p1.package_id, revision_ref=t2.name)
        assert p2 == p1

        tags = backend.tag_list(p1.package_id)
        assert len(tags) == 1
        assert tags[0].description == 'My newer better tag'

    def test_tag_update_desc_only(self, backend):
        p1 = backend.create(self.dataset_id('mydataset'), create_test_datapackage('mydataset'))
        t1 = backend.tag_create(p1.package_id, p1.revision, 'version-1.0', description="My nice little tag")
        backend.tag_update(p1.package_id, t1.name, new_description='My newer better tag')

        p2 = backend.fetch(p1.package_id, revision_ref=t1.name)
        assert p2 == p1

        tags = backend.tag_list(p1.package_id)
        assert len(tags) == 1
        assert tags[0].description == 'My newer better tag'

    def test_tag_update_name_only(self, backend):
        p1 = backend.create(self.dataset_id('mydataset'), create_test_datapackage('mydataset'))
        t1 = backend.tag_create(p1.package_id, p1.revision, 'version-1.0', description="My nice little tag")
        t2 = backend.tag_update(p1.package_id, t1.name, new_name='v-1.0')

        with pytest.raises(exc.NotFound):
            backend.fetch(p1.package_id, revision_ref=t1.name)

        p2 = backend.fetch(p1.package_id, revision_ref=t2.name)
        assert p2 == p1

        tags = backend.tag_list(p1.package_id)
        assert len(tags) == 1
        assert tags[0].description == 'My nice little tag'
        assert tags[0].name == 'v-1.0'

    def test_tag_update_no_chance(self, backend):
        p1 = backend.create(self.dataset_id('mydataset'), create_test_datapackage('mydataset'))
        t1 = backend.tag_create(p1.package_id, p1.revision, 'version-1.0', description="My nice little tag")
        with pytest.raises(ValueError):
            backend.tag_update(p1.package_id, t1.name)

    def test_tag_update_existing_name(self, backend):
        p1 = backend.create(self.dataset_id('mydataset'), create_test_datapackage('mydataset'))
        t1 = backend.tag_create(p1.package_id, p1.revision, 'version-1.0', description="My nice little tag")
        p2 = backend.update(self.dataset_id('mydataset'), create_test_datapackage('mydataset', type='csv'))
        t2 = backend.tag_create(p1.package_id, p2.revision, 'version-1.1', description="My next version tag")

        with pytest.raises(exc.Conflict):
            backend.tag_update(p1.package_id, t1.name, new_name=t2.name)

        tags = backend.tag_list(p1.package_id)
        assert len(tags) == 2

    def test_tag_update_no_tag(self, backend):
        p1 = backend.create(self.dataset_id('mydataset'), create_test_datapackage('mydataset'))
        with pytest.raises(exc.NotFound):
            backend.tag_update(p1.package_id, 'version-1.0', new_name='v-1.0')

    def test_tag_update_no_package(self, backend):
        with pytest.raises(exc.NotFound):
            backend.tag_update(self.dataset_id('mydataset'), 'version-1.0', new_name='v-1.0')

    def test_tag_update_invalid_name(self, backend):
        p1 = backend.create(self.dataset_id('mydataset'), create_test_datapackage('mydataset'))
        t1 = backend.tag_create(p1.package_id, p1.revision, 'version-1.0', description="My nice little tag")

        with pytest.raises(ValueError):
            backend.tag_update(p1.package_id, t1.name, new_name='ver 1.0')

    def test_tag_delete(self, backend):
        p1 = backend.create(self.dataset_id('mydataset'), create_test_datapackage('mydataset'))
        backend.tag_create(p1.package_id, p1.revision, 'version-1.0', description="First version")
        p2 = backend.update(self.dataset_id('mydataset'), create_test_datapackage('mydataset', type='csv'))
        backend.tag_create(p1.package_id, p2.revision, 'version-1.1', description="Second version")
        p3 = backend.create(self.dataset_id('otherdataset'), create_test_datapackage('otherdataset'))
        backend.tag_create(p3.package_id, p3.revision, 'version-1.0', description="First version")

        tags = backend.tag_list(self.dataset_id('mydataset'))
        assert len(tags) == 2

        backend.tag_delete(p1.package_id, 'version-1.0')

        tags = backend.tag_list(self.dataset_id('mydataset'))
        assert 1 == len(tags)
        assert 1 == len(backend.tag_list(self.dataset_id('otherdataset')))
        assert tags[0].name == 'version-1.1'

    def test_tag_delete_no_tag(self, backend):
        p1 = backend.create(self.dataset_id('mydataset'), create_test_datapackage('mydataset'))
        backend.tag_create(p1.package_id, p1.revision, 'version-1.0', description="First version")

        with pytest.raises(exc.NotFound):
            backend.tag_delete(p1.package_id, 'version-1.1')

    def test_tag_delete_no_package(self, backend):
        p1 = backend.create(self.dataset_id('mydataset'), create_test_datapackage('mydataset'))
        backend.tag_create(p1.package_id, p1.revision, 'version-1.0', description="First version")

        with pytest.raises(exc.NotFound):
            backend.tag_delete(self.dataset_id('otherdataset'), 'version-1.0')
