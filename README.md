metastore-lib: metadata storage library for datapackages
========================================================

[![Build Status](https://travis-ci.org/datopian/giftless.svg?branch=master)](https://travis-ci.org/datopian/metastore-lib)
[![Maintainability](https://api.codeclimate.com/v1/badges/58f05c5b5842c8bbbdbb/maintainability)](https://codeclimate.com/github/datopian/metastore-lib/maintainability)
[![Test Coverage](https://api.codeclimate.com/v1/badges/58f05c5b5842c8bbbdbb/test_coverage)](https://codeclimate.com/github/datopian/metastore-lib/test_coverage)

A Python library for abstracting metadata storage for [datapackage.json][1]
packages. 

Quick Start
-----------

To use the library after you have installed it, first instantiate a storage
instance:

```python
config = {"token": "...",
          "more_options": "..."}
          
# Using the provided factory method
metastore = create_metastore('github', **config)

# Or by directly instantiating one of the MetaStoreBackend classes:
metastore = GitHubMetaStore(**config)
```
 
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
the stored package:

```python
class PackageInfo:
    id = "..."
    revision = "..."
    tag = None
    package = {"what": "the datapackage contents ..."}
    ... TBD ... 
```
 
To update the same package:

```python
base_rev = package_info.revision
new_metadata ={"type": "csv"}
package_info = metastore.update(package_id, new_metadata, base_revision=base_rev)
```

This will update the package, creating a new revision of the metadata. Note that 
`base_revision` is not required but is recommended, to ensure changes are not 
conflicting; Specifying `base_revision` will ensure you are changing based on 
the latest revision of the package, and if not a `ConflictException` will be 
raised. 

### Package Identifiers

TBD

License
-------
Copyright (C) 2020, Viderum, Inc. 

Giftless is free / open source software and is distributed under the terms of 
the MIT license. See [LICENSE](LICENSE) for details.  


 [1]: http://specs.frictionlessdata.io/data-package/
