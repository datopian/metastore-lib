.. metastore-lib documentation master file, created by
   sphinx-quickstart on Thu May 28 17:07:52 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome
=======

`metastore-lib` is a Python library for abstracting metadata storage for
datapackage.json_ packages.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   backends/index
   api

Quick Start
===========

Instantiating a backend
-----------------------

To use the library after you have installed it, first instantiate a
storage instance:

.. code:: python

   config = {"token": "...",
             "more_options": "..."}

   # Using the provided factory method
   metastore = create_metastore('github', **config)

   # Or by directly instantiating one of the MetaStoreBackend classes:
   metastore = GitHubStorage(**config)

Basic Usage Examples
--------------------

Storing a dataset (creating a new package)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Then use the storage instance to store a dataset:

.. code:: python

   import json

   with open("datapackage.json") as f:
       metadata = json.loads(f)

   package_info = metastore.create(package_id, metadata)

This will store the package metadata using the specific storage backend.
For example, in the case of the GitHub backend, a new repository will be
created with a corresponding ``datapackage.json`` file and LFS pointer
files for resources.

The returned ``package_info`` will be an object with some information
about the stored package revision:

.. code:: python

   class PackageRevisionInfo:
       package_id: str = "..."
       revision: str = "..."
       package: Dict = {"name": "mypackage",
                        "version": "1.0.0",
                        "resources": [
                          # ...
                        ]}

Updating a dataset
^^^^^^^^^^^^^^^^^^

To update the same package:

.. code:: python

   base_rev = package_info.revision
   metadata['version'] = '1.0.1'
   package_info = metastore.update(package_id, metadata, base_revision=base_rev)

This will update the package, creating a new revision of the metadata.
Note that ``base_revision`` is not required but is recommended, to
ensure changes are not conflicting; Specifying ``base_revision`` will
ensure you are changing based on the latest revision of the package, and
if not a ``ConflictException`` will be raised.

Listing Dataset Revisions
^^^^^^^^^^^^^^^^^^^^^^^^^

Now you can get a list of all revisions of the package (there should be
exactly two):

.. code:: python

   revisions = metastore.revision_list(package_id)
   # Returns: [ <RevisionInfo rev2>, <RevisionInfo rev1> ]

Each returned object in the list represents a single revision:

.. code:: python

   class PackageRevisionInfo:
       package_id: str = "..."
       revision: str = "..."
       created: datetime = ... # the revision creation timestamp


Fetching a Dataset Revision
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Now that we have two different revisions of the dataset, we can fetch a
specific revision of the metadata:

.. code:: python

   package_info = metastore.fetch(package_id, revision=revisions[0].revision)
   print(f"{package_info.package['name']} {package_info.package['version']}")
   # will output: mypackage 1.0.0

   package_info = metastore.fetch(package_id, revision=revisions[1].revision)
   print(f"{package_info.package['name']} {package_info.package['version']}")
   # will output: mypackage 1.0.1

This returns a ``RevisionInfo`` object for the requested package /
revision.

Note that the ``revision`` parameter is optional, and if omitted the
latest revision will be fetched.

Creating a Tag
^^^^^^^^^^^^^^

Once a revision has been created, you can tag the revision to give it a
meaningful name:

.. code:: python

   tag_info = metastore.tag_create(package_id,
                                   revision=revisions[1].revision,
                                   name='ver-1.0.1')

This will return a new ``TagInfo`` object, with the ``name`` attribute
set to ``'ver-1.0.1'``.

Listing Tags
^^^^^^^^^^^^

To get a list of all tags for a package:

.. code:: python

   tags = metastore.tag_list(package_id)

This will return a list of ``TagInfo`` objects, each pointing to a
specific tagged revision.

A Note on Package Identifiers
-----------------------------

Package Identifiers (e.g. the ``package_id`` in the example above) are
strings and are, as far as ``metastore`` is concerned, opaque. However,
they may still be meaningful as far as either the backend or the client
is concerned.

For example, with a GitHub based backend you will use IDs that correlate
with ``<org name>/<repo name>`` structure.

Other backends may expect you to use UUID type identifiers.

It is up to the code using the ``metastore`` library to be able to
compose the right identifiers.

Using the Filesystem Backend for Testing
----------------------------------------

For testing and quick prototyping purposes, this library offers a
special ``filesystem`` backend, which can be used to save versioned
datapackage information on the file system, in memory or on virtual file
system.

This backend is based on the `PyFilesystem`_ library, and can use any of
it's supported file systems as storage.

In testing, it is recommended to use a memory based storage:

.. code:: python

   from metastore.backend.filesystem import FilesystemStorage

   def test_my_code():
       """Test for code that relies on a metastore-lib backend
       """
       backend = FilesystemStorage('mem://')
       r1 = backend.create('some-package', datapackage, 'Initial revision')
       # ... continue with testing ...

The ``FilesystemStorage`` constructor takes a single argument, which is
a ``PyFilesystem`` root filesystem URL.

Beyond this, all API is exactly the same as with other backends.

Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. _datapackage.json: http://specs.frictionlessdata.io/data-package/
.. _PyFilesystem: https://docs.pyfilesystem.org/
