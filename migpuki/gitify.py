#!/usr/bin/env python3
# requirements: Python 3.5, git

import argparse
import glob
import gzip
import os
import os.path
import re
import shutil
import subprocess
import sys
from collections import namedtuple
from datetime import datetime, timezone, timedelta

Commit = namedtuple('Commit', ['unixtime', 'path', 'data', 'latest'])
Rename = namedtuple('Rename', ['unixtime', 'oldpath', 'newpath'])
unixtime_re = re.compile(r'\s*\>{10}\s+(\d+)\s*')
renamelog_date_re = re.compile(r'\s*\*(\d+)-(\d+)-(\d+)\s*\(.+?\)\s*(\d+):(\d+):(\d+)\s*')
renamelog_from_re = re.compile(r'\s*--From:\[\[(.+?)\]\]\s*')
renamelog_to_re = re.compile(r'\s*--To:\[\[(.+?)\]\]\s*')

class Gitify:
    def __init__(self, basedir, *, verbose=False, outdir='wiki-repo', name=None, email=None):
        self.basedir = basedir
        self.verbose = verbose
        self.outdir = outdir
        self.name = name
        self.email = email

        self.commit_history = []     # [Commit]
        self.rename_history = set()  # {Rename}
        self.all_history = []        # [Commit | Rename]
        self._debug_count = 100

    def run(self):
        if os.path.exists(self.outdir):
            print('output directory "{}" already exists.'.format(self.outdir), file=sys.stderr)
            exit(1)
        self.commit_history = []
        self.generate_commit_history()
        self.rename_history = set()
        self.generate_rename_history()
        self.all_history = self.commit_history + list(self.rename_history)
        self.all_history.sort()
        self.check_rename()
        self.generate_git_repository()

    def generate_commit_history(self):
        pattern = os.path.join(self.basedir, 'backup/**/*.txt')
        prefixlen = len(os.path.join(self.basedir, 'backup') + os.sep)
        for oldpath in glob.iglob(pattern, recursive=True):
            if oldpath.endswith('backup/_RenameLog.txt'):
                continue
            with open(oldpath) as oldfile:
                path = oldpath[prefixlen:]
                self.read_and_extend_history(oldfile, path)
            if self._debug_count and len(self.commit_history) > self._debug_count / 3:
                break
        pattern = os.path.join(self.basedir, 'backup/**/*.gz')
        for oldpath in glob.iglob(pattern, recursive=True):
            if oldpath.endswith('backup/_RenameLog.gz'):
                continue
            with gzip.open(oldpath) as oldfile:
                path = oldpath[prefixlen:-3] + '.txt'
                self.read_and_extend_history(oldfile, path)
            if self._debug_count and len(self.commit_history) > self._debug_count * 2 / 3:
                break
        pattern = os.path.join(self.basedir, 'wiki/**/*.txt')  # latest
        prefixlen = len(os.path.join(self.basedir, 'wiki') + os.sep)
        for oldpath in glob.iglob(pattern, recursive=True):
            if oldpath.endswith('wiki/_RenameLog.txt'):
                continue
            with open(oldpath) as oldfile:
                path = oldpath[prefixlen:]
                self.read_and_extend_history(oldfile, path)
            if self._debug_count and len(self.commit_history) > self._debug_count:
                break

    def generate_rename_history(self):
        pattern = os.path.join(self.basedir, '*/_RenameLog.*')
        for path in glob.iglob(pattern, recursive=True):
            openf = open
            if path.endswith('.gz'):
                openf = gzip.open
            with openf(path) as file:
                self.read_and_update_rename_history(file)
        print(self.rename_history)

    def read_and_extend_history(self, oldfile, path):
        self.commit_history.extend(self.read_history(oldfile, path))

    def read_history(self, oldfile, path):
        history = []
        unixtime = None
        buf = ''
        latest = False
        for line in oldfile:
            if hasattr(line, 'decode'):
                line = line.decode('utf-8')
            match = unixtime_re.match(line)
            if match:
                if unixtime != None:
                    history.append(Commit(unixtime, path, buf, latest))
                    buf = ''
                unixtime = int(match.group(1))
            else:
                buf += line
        if unixtime == None:
            unixtime = datetime.now(timezone.utc).timestamp()
            latest = True
        history.append(Commit(unixtime, path, buf, latest))
        return history

    def read_and_update_rename_history(self, file):
        history = self.read_rename_history(file)
        self.rename_history.update(history)

    def read_rename_history(self, file):
        history = set()
        unixtime = None
        page_from = None
        for line in file:
            if hasattr(line, 'decode'):
                line = line.decode('utf-8')
            line = line.strip()
            match = renamelog_date_re.match(line)
            if match:
                y, mo, d, h, mi, s = map(int, match.groups())
                unixtime = datetime(y, mo, d, h, mi, s, 0).timestamp()
                continue
            match = renamelog_from_re.match(line)
            if match:
                page_from = match.group(1)
                continue
            match = renamelog_to_re.match(line)
            if match:
                page_to = match.group(1)
                history.add(Rename(unixtime, page_from + ".txt", page_to + ".txt"))
                unixtime = None
                page_from = None
                continue
        return history

    def check_rename(self):
        for item in reversed(self.all_history):
            if type(item) == Commit:
                pass
            elif type(item) == Rename:
                print(item)
                pass
            else:
                assert("Unknown Type: " + str(type(item)))

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
        for item in self.all_history:
            if type(item) == Commit:
                self.commit(item)
            elif type(item) == Rename:
                self.rename(item)
            else:
                assert("Unknown Type: " + str(type(item)))
        self.commit_latests()
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
        if commit.latest:
            return
        # http://stackoverflow.com/questions/3878624/how-do-i-programmatically-determine-if-there-are-uncommited-changes
        proc = subprocess.run(['git', 'diff-index', '--quiet', 'HEAD', '--'])
        if proc.returncode == 0:
            return
        proc = subprocess.run(['git', 'commit', '-m', commit.path + ' (PukiWiki)'])
        if proc.returncode != 0:
            raise Exception('failed: git commit ({}), return code: {}'.format(commit.path, proc.returncode))

    def rename(self, rename):
        proc = subprocess.run(['git', 'mv', rename.oldpath, rename.newpath])
        if proc.returncode != 0:
            return # raise Exception('failed: git mv {} {}, return code: {}'.format(rename.oldpath, rename.newpath, proc.returncode))
        proc = subprocess.run(['git', 'diff-index', '--quiet', 'HEAD', '--'])
        if proc.returncode == 0:
            return
        proc = subprocess.run(['git', 'commit', '-m', rename.oldpath + ' -> ' + rename.newpath + ' (PukiWiki)'])
        if proc.returncode != 0:
            raise Exception('failed: git commit ({}), return code: {}'.format(commit.path, proc.returncode))

    def commit_latests(self):
        proc = subprocess.run(['git', 'diff-index', '--quiet', 'HEAD', '--'])
        if proc.returncode == 0:
            return
        proc = subprocess.run(['git', 'commit', '-m', 'migrated from PukiWiki using migpuki'])
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
