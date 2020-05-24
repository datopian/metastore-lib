from os import path
from setuptools import setup

here = path.abspath(path.dirname(__file__))

# Get the long description from the relevant file
with open(path.join(here, 'README.md')) as f:
    long_description = f.read()

setup(
    name='metastore-lib',
    packages=['metastore'],
    version=open('VERSION').read(),
    description='A library for abstracting versioned metadata storage for data packages',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Shahar Evron',
    author_email='shahar.evron@datopian.com',
    install_requires=[
        'pytz',
        'pygithub',
    ],
    package_data={}
)
