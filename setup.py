from setuptools import setup, find_packages
from migpuki import __version__

setup(name='migpuki',
      version=__version__,
      description='scripts for migration from PukiWiki',
      author='taskie',
      author_email='t@skie.jp',
      url='https://github.com/taskie/migpuki',
      packages=find_packages(),
      entry_points="""
      [console_scripts]
      migpuki-utf8ify = migpuki.utf8ify:main
      migpuki-gitify = migpuki.gitify:main
      """,)
