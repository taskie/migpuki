#!/usr/bin/env python3
# requirements: Python 3.5, git

import argparse
import glob
import gzip
import os
import os.path
import shutil
import sys
import re
import subprocess
from collections import namedtuple
from datetime import datetime, timezone, timedelta

Commit = namedtuple('Commit', ['unixtime', 'path', 'data'])
unixtime_re = re.compile(r'^\s*\>{10}\s+(\d+)\s*$')

class Gitify:
    def __init__(self, basedir, *, verbose=False, outdir='wiki-repo', name=None, email=None):
        self.basedir = basedir
        self.verbose = verbose
        self.outdir = outdir
        self.name = name
        self.email = email
        self._debug_count = 0

    def run(self):
        if os.path.exists(self.outdir):
            print('output directory "{}" already exists.'.format(self.outdir), file=sys.stderr)
            exit(1)
        self.all_history = []
        self.generate_all_history()
        self.all_history.sort()
        self.generate_git_repository()

    def generate_all_history(self):
        pattern = os.path.join(self.basedir, 'backup/**/*.txt')
        prefixlen = len(os.path.join(self.basedir, 'backup') + os.sep)
        for oldpath in glob.iglob(pattern, recursive=True):
            with open(oldpath) as oldfile:
                path = oldpath[prefixlen:]
                self.read_and_extend_history(oldfile, path)
            if self._debug_count and len(self.all_history) > self._debug_count / 2:
                break
        pattern = os.path.join(self.basedir, 'backup/**/*.gz')
        for oldpath in glob.iglob(pattern, recursive=True):
            with gzip.open(oldpath) as oldfile:
                path = oldpath[prefixlen:-3] + '.txt'
                self.read_and_extend_history(oldfile, path)
            if self._debug_count and len(self.all_history) > self._debug_count:
                break

    def read_and_extend_history(self, oldfile, path):
        self.all_history.extend(self.read_history(oldfile, path))

    def read_history(self, oldfile, path):
        history = []
        unixtime = None
        buf = ''
        for line in oldfile:
            if hasattr(line, 'decode'):
                line = line.decode('utf-8')
            match = unixtime_re.match(line)
            if match:
                if unixtime != None:
                    history.append(Commit(unixtime, path, buf))
                    buf = ''
                unixtime = int(match.group(1))
            else:
                buf += line
        if unixtime != None:
            # in memory...
            history.append(Commit(unixtime, path, buf))
        return history

    def generate_git_repository(self):
        os.makedirs(self.outdir)
        oldcwd = os.getcwd()
        os.chdir(self.outdir)
        proc = subprocess.run(['git', 'init'], stdout=subprocess.PIPE)
        self.printv(proc.stdout.decode('utf-8'), end='')
        if self.name:
            subprocess.run(['git', 'config', 'user.name', self.name])
        if self.email:
            subprocess.run(['git', 'config', 'user.email', self.email])
        for commit in self.all_history:
            self.commit(commit)
        os.chdir(oldcwd)

    def printv(self, *args, **kwargs):
        if self.verbose:
            print(*args, **kwargs)

    def commit(self, commit):
        date = datetime.utcfromtimestamp(commit.unixtime).isoformat()
        os.environ['GIT_COMMITTER_DATE'] = date
        os.environ['GIT_AUTHOR_DATE'] = date
        dirname = os.path.dirname(commit.path)
        if dirname and not os.path.exists(dirname):
            os.makedirs(dirname)
        with open(commit.path, 'w') as file:
            file.write(commit.data)
        proc = subprocess.run(['git', 'add', commit.path])
        if proc.returncode != 0:
            raise Exception('failed: git add {}, return code: {}'.format(commit.path, proc.returncode))
        # http://stackoverflow.com/questions/3878624/how-do-i-programmatically-determine-if-there-are-uncommited-changes
        proc = subprocess.run(['git', 'diff-index', '--quiet', 'HEAD', '--'])
        if proc.returncode == 0:
            return
        proc = subprocess.run(['git', 'commit', '-m', commit.path + ' (PukiWiki)'])
        if proc.returncode != 0:
            raise Exception('failed: git commit ({}), return code: {}'.format(commit.path, proc.returncode))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='utf8ize PukiWiki data.')
    parser.add_argument('basedir',
                        help='UTF-8ized PukiWiki root directory (which has wiki / backup directories)')
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true', default=False,
                        help='show verbose log')
    parser.add_argument('-o', '--outdir', default='wiki-repo',
                        help='output directory name')
    parser.add_argument('-n', '--name', help='Git author / committer name')
    parser.add_argument('-e', '--email', help='Git author / committer email')
    params = parser.parse_args()

    gitify = Gitify(basedir=params.basedir,
                    verbose=params.verbose,
                    outdir=params.outdir,
                    name=params.name,
                    email=params.email)
    gitify.run()
