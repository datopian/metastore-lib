# metastore-lib: metadata storage library with versioning

[![Build Status](https://travis-ci.org/datopian/metastore-lib.svg?branch=master)](https://travis-ci.org/datopian/metastore-lib)
[![Maintainability](https://api.codeclimate.com/v1/badges/f53acd8aa367512130c3/maintainability)](https://codeclimate.com/github/datopian/metastore-lib/maintainability)
[![Test Coverage](https://api.codeclimate.com/v1/badges/f53acd8aa367512130c3/test_coverage)](https://codeclimate.com/github/datopian/metastore-lib/test_coverage)
[![PyPI version](https://badge.fury.io/py/metastore-lib.svg)](https://badge.fury.io/py/metastore-lib)
[![Documentation Status](https://readthedocs.org/projects/metastore-lib/badge/?version=latest)](https://metastore-lib.readthedocs.io/en/latest/?badge=latest)

Library for storing (dataset) metadata, with versioning support and pluggable backends including GitHub. Written in Python (there's also a [JS version][js]). Designed around pluggable backends it comes with a full implementations for GitHub and the Filesystem. Originally designed for datasets it can be used for storing any kind of metadata. Versioning (revisioning) support is built-in e.g. you can do: `fetch(objectId, revision) => metadata at that revision of the object`

[js]: https://github.com/datopian/metastore-lib-js

## Features

* Simple and lightweight (minimal dependencies)
* Well defined interface honed over the years: create, delete, fetch etc
* Support for [versioning/revisioning][ver] e.g. `fetch(dataset_id, revision_id)` plus versioning specific items such as revisions and releases (tags)
* Pluggable backends with support for GitHub and Filesystem out of the box 

[ver]: https://tech.datopian.com/versioning/


## Full Documentation

This README provides some basic information on how to get started. However, the 
most up-to-date and comprehesive documentation for `mestastore-lib` is 
[available at metastore-lib.readthedocs.io](https://metastore-lib.readthedocs.io/en/latest).

## Installation

The easiest way to install the latest stable version of metastore-lib into
your Python environment is via `pip`:

    pip install metastore-lib

## Quick Start

### Instantiating a backend

To use the library after you have installed it, first instantiate a storage
instance:

```python
config = {"token": "...",
          "more_options": "..."}
          
# Using the provided factory method
metastore = create_metastore('github', **config)

# Or by directly instantiating one of the MetaStoreBackend classes:
metastore = GitHubStorage(**config)
```

### Storing a dataset (creating a new package)
 
Then use the storage instance to store a dataset:

```python
import json

with open("datapackage.json") as f:
    metadata = json.loads(f)

package_info = metastore.create(package_id, metadata)
```

This will store the package metadata using the specific storage backend. For 
example, in the case of the GitHub backend, a new repository will be created
with a corresponding `datapackage.json` file and LFS pointer files for 
resources.

The returned `package_info` will be an object with some information about
the stored package revision:

```python
class PackageRevisionInfo:
    package_id: str = "..."
    revision: str = "..."
    package: Dict = {"name": "mypackage",
                     "version": "1.0.0",    
                     "resources": [
                       # ...
                     ]}
```

### Updating a dataset

To update the same package:

```python
base_rev = package_info.revision
metadata['version'] = '1.0.1'
package_info = metastore.update(package_id, metadata, base_revision=base_rev)
```

This will update the package, creating a new revision of the metadata. Note that 
`base_revision` is not required but is recommended, to ensure changes are not 
conflicting; Specifying `base_revision` will ensure you are changing based on 
the latest revision of the package, and if not a `ConflictException` will be 
raised. 

### Listing Dataset Revisions

Now you can get a list of all revisions of the package (there should be exactly two):

```python
revisions = metastore.revision_list(package_id)
# Returns: [ <RevisionInfo rev2>, <RevisionInfo rev1> ]
```

Each returned object in the list represents a single revision:

```python
class PackageRevisionInfo:
    package_id: str = "..."
    revision: str = "..."
    created: datetime = ... # the revision creation timestamp
    
```

### Fetching a Dataset Revision

Now that we have two different revisions of the dataset, we can fetch a 
specific revision of the metadata:

```python
package_info = metastore.fetch(package_id, revision=revisions[0].revision)
print(f"{package_info.package['name']} {package_info.package['version']}")
# will output: mypackage 1.0.0

package_info = metastore.fetch(package_id, revision=revisions[1].revision)
print(f"{package_info.package['name']} {package_info.package['version']}")
# will output: mypackage 1.0.1
```

This returns a `RevisionInfo` object for the requested package / revision.

Note that the `revision` parameter is optional, and if omitted the latest 
revision will be fetched. 

### Creating a Tag

Once a revision has been created, you can tag the revision to give it a 
meaningful name:

```python
tag_info = metastore.tag_create(package_id, 
                                revision=revisions[1].revision, 
                                name='ver-1.0.1')
```

This will return a new `TagInfo` object, with the `name` attribute set to
`'ver-1.0.1'`. 

### Listing Tags 

To get a list of all tags for a package:

```python
tags = metastore.tag_list(package_id)
```

This will return a list of `TagInfo` objects, each pointing to a specific
tagged revision. 

## A Note on Package Identifiers

Package Identifiers (e.g. the `package_id` in the example above) are strings
and are, as far as `metastore` is concerned, opaque. However, they may still
be meaningful as far as either the backend or the client is concerned. 

For example, with a GitHub based backend you will use IDs that correlate with
`<org name>/<repo name>` structure. 

Other backends may expect you to use UUID type identifiers. 

It is up to the code using the `metastore` library to be able to compose the 
right identifiers. 

## Using the Filesystem Backend for Testing

For testing and quick prototyping purposes, this library offers a special 
`filesystem` backend, which can be used to save versioned datapackage 
information on the file system, in memory or on virtual file system. 

This backend is based on the [PyFilesystem](https://docs.pyfilesystem.org/)
library, and can use any of it's supported file systems as storage. 

In testing, it is recommended to use a memory based storage:

```python
from metastore.backend.filesystem import FilesystemStorage

def test_my_code():
    """Test for code that relies on a metastore-lib backend
    """
    backend = FilesystemStorage('mem://')
    r1 = backend.create('some-package', datapackage, 'Initial revision') 
    # ... continue with testing ...
```

The `FilesystemStorage` constructor takes a single argument, which is a
`PyFilesystem` root filesystem URL. 

Beyond this, all API is exactly the same as with other backends. 


## License

Copyright (C) 2020, Datopian (Viderum, Inc). 

metastore-lib is free / open source software and is distributed under the terms of 
the MIT license. See [LICENSE](LICENSE) for details.  

[1]: http://specs.frictionlessdata.io/data-package/
