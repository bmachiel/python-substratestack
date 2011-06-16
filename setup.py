#!/bin/env python

from os import path
from setuptools import setup
from subprocess import Popen, PIPE

# check whether we're installing from an sdist archive or not
if path.exists('PKG-INFO'):
    from substratestack import __version__ as version
else:
    # write the git version to substratestack/version.py
    # based on version.py by Douglas Creager <dcreager@dcreager.net>
    # http://dcreager.net/2010/02/10/setuptools-git-version-numbers/
    try:
        p = Popen(['git', 'describe', '--abbrev=4'],
                  stdout=PIPE, stderr=PIPE)
        p.stderr.close()
        line = p.stdout.readlines()[0]
        version = line.strip()[1:]
    except:
        print("A problem occured while trying to run git. "
              "Version information is unavailable!")
        version = 'unknown'

    version_file = open('substratestack/version.py', 'w')
    version_file.write("__version__ = '%s'\n" % version)
    version_file.close()


setup(
    name='substratestack',
    version=version,
    packages=['substratestack'],
    requires=['reportlab'],
    provides=['substratestack'],
    
    author="Brecht Machiels",
    author_email="brecht.machiels@esat.kuleuven.be",
    description=("Python package to simplify substrate stackups and export "
                 "them for use in Momentum and Sonnet"),
    url="http://github.com/bmachiel/python-substratestack",
    license="BSD (2-clause)",
    keywords="substrate stack ADS Momentum Sonnet em",
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)
