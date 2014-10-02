#!/bin/env python
# -*- coding: utf8 -*-

from setuptools import setup, find_packages

version = "0.2.1"

setup(
    name="tempi",
    version=version,
    description="Add tempo metadata to your music collection.",
    classifiers=[
        "Topic :: Multimedia :: Sound/Audio :: Analysis",
    ],
    keywords="music tempo bpm echonest",
    author="Luke Macken",
    author_email="lmacken@redhat.com",
    url="https://github.com/lmacken/tempi",
    license="GPLv3",
    packages=find_packages(),
    scripts=[
    ],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        "pyechonest",
        "mutagen",
        "progressbar",
        "fabulous",
    ],
    entry_points="""
    [console_scripts]
    tempi = tempi.main:main
    """
)
