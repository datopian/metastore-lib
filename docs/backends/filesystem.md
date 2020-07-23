# `filesystem` - PyFilesystem based Storage
The `filesystem` backend can use any filesystem-like storage that is 
supported by [PyFilesystem](https://docs.pyfilesystem.org/).

## Local Filesystem Storage
Most notably, the `filesystem` backend can be used to store metadata in, well, 
your local file system. This is typically useful in very small, PoC or test 
setups or for automated testing where storage state needs to be preserved 
between isolated tests (and the `mem://` backend will not suffice). 

To store metadata locally, simply instantiate using the `filesystem` backend
and the `"uri"` option pointing to a local directory:  

```python
import metastore

backend = metastore.create_metastore('filesystem', {"uri": "./metastore"})
```

Note that the local directlry (in our case `./metastore` relative to the 
current working directory) must exist before `backend` can be instantiated 
and used. 

## In-Memory Storage for Testing Purposes
Another potential use of this backend is when writing tests for code that uses 
`metastore-lib`. instead of mocking out `metastore-lib` code, one can simply 
use the `mem` filesystem when instantiating a `metastore-lib` backend instance:

```python
import metastore

backend = metastore.create_metastore('filesystem', {"uri": "mem://"})
```

This backend object will only store metadata in the process memory, and only
for as long as the `backend` object is alive. Once the object is destroyed 
(e.g. at the end of a test), all data stored in it will be destroyed as well. 
This comes in handy in testing because it is a super-fast, limited state 
storage, which doesn't require any special cleanup procedures between tests.

## Other Filesystem-Like Backends
PyFilesystem abstracts a large number of filesystem like storage backends, 
and all of them can be used with `metastore-lib` assuming you have the proper
dependencies installed. 

All you need to do is provide the right 
[PyFilesystem URL](https://docs.pyfilesystem.org/en/latest/openers.html) as 
the `"uri"` configuration option when instantiating the backend. 

See https://docs.pyfilesystem.org/en/latest/builtin.html for a full list of
built-in supported filysystems, and 
https://docs.pyfilesystem.org/en/latest/implementers.html for details on how
to implement your own filesystem abstraction. 
