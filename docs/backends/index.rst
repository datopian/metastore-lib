Storage Backends
================

Overview
--------
``metastore-lib`` abstracts versioned storage backends, and supports different
storage backends out of the box. The following storage backends are currently
provided:

* ``filesystem`` - a "fliesystem-like" storage backend that can use your local
  file system, in-process memory or any filesystem-like storage supported by
  [PyFilesystem](https://docs.pyfilesystem.org/).
* ``github`` - stores metadata in a GitHub repository using the GitHub API

The Storage Backend Factory
---------------------------

You can get an instance of *any* supported backend by providing the backend
type and a configuration ``dict`` to the provided factory function
``create_metastore``::

    import metastore

    # Create an in-memory storage backend
    config = {"uri": "mem://"}
    backend = metastore.create_metastore('filesystem', config)

Storage Backends
----------------

.. toctree::
   :maxdepth: 2

   filesystem
   github
