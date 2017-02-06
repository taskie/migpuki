#!/usr/bin/env python3

from setuptools import setup, find_packages
from migpuki import __version__

setup(name='migpuki',
      version=__version__,
      description='scripts for migration from PukiWiki',
      author='taskie',
      author_email='t@skie.jp',
      url='https://github.com/taskie/migpuki',
      license='Apache License 2.0',
      keywords=['pukiwiki'],
      packages=find_packages(),
      entry_points="""
      [console_scripts]
      migpuki-utf8ify = migpuki.utf8ify:main
      migpuki-gitify = migpuki.gitify:main
      """,)
