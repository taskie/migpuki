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

Commit = namedtuple('Commit', ['unixtime', 'path', 'data'])
Rename = namedtuple('Rename', ['unixtime', 'oldpath', 'newpath'])
unixtime_re = re.compile(r'\s*\>{10}\s+(\d+)\s*')
renamelog_date_re = re.compile(r'\s*\*(\d+)-(\d+)-(\d+)\s*\(.+?\)\s*(\d+):(\d+):(\d+)\s*')
renamelog_from_re = re.compile(r'\s*--From:\[\[(.+?)\]\]\s*')
renamelog_to_re = re.compile(r'\s*--To:\[\[(.+?)\]\]\s*')

class Gitify:
    def __init__(self, basedir, *, verbose=False, outdir='wiki-repo', name=None, email=None, renamelog=False):
        self.basedir = basedir
        self.basedir_abs = os.path.abspath(self.basedir)
        self.verbose = verbose
        self.outdir = outdir
        self.name = name
        self.email = email
        self.renamelog = renamelog

        self.commit_history = []     # [Commit]
        self.rename_history = set()  # {Rename}
        self.all_history = []        # [Commit | Rename]
        self._debug_count = 0

    def run(self):
        if os.path.exists(self.outdir):
            print('output directory "{}" already exists.'.format(self.outdir), file=sys.stderr)
            exit(1)
        self.commit_history = []
        print("reading pukiwiki data...")
        self.generate_commit_history()
        self.rename_history = set()
        if self.renamelog:
            self.generate_rename_history()
        print("creating new history...")
        self.all_history = self.commit_history + list(self.rename_history)
        self.all_history.sort()
        if self.renamelog:
            self.rename_paths_in_all_history()
        print("generating git repo...")
        self.generate_git_repository()

    def generate_commit_history(self):
        pattern = os.path.join(self.basedir, 'backup/**/*.txt')
        prefixlen = len(os.path.join(self.basedir, 'backup') + os.sep)
        for oldpath in glob.iglob(pattern, recursive=True):
            path = oldpath[prefixlen:]
            if path == '_RenameLog.txt':
                continue
            with open(oldpath) as oldfile:
                self.read_and_extend_commit_history(oldfile, path)
            if self._debug_count and len(self.commit_history) > self._debug_count / 2:
                break
        pattern = os.path.join(self.basedir, 'backup/**/*.gz')
        for oldpath in glob.iglob(pattern, recursive=True):
            path = oldpath[prefixlen:-3] + '.txt'
            if path == '_RenameLog.txt':
                continue
            with gzip.open(oldpath) as oldfile:
                self.read_and_extend_commit_history(oldfile, path)
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

    def read_and_extend_commit_history(self, oldfile, path):
        self.commit_history.extend(self.read_commit_history(oldfile, path))

    def read_commit_history(self, oldfile, path):
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
        if unixtime == None:
            unixtime = datetime.now(timezone.utc).timestamp()
        history.append(Commit(unixtime, path, buf))
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
                unixtime = int(datetime(y, mo, d, h, mi, s, 0).timestamp())
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

    def rename_paths_in_all_history(self):
        new_history = []
        latest_to_old_map = {}
        old_to_latest_map = {}
        for item in reversed(self.all_history):
            if type(item) == Commit:
                unixtime, path, data = item
                if path in latest_to_old_map:
                    path = latest_to_old_map[path]
                new_history.append(Commit(unixtime, path, data))
            elif type(item) == Rename:
                unixtime, oldpath, newpath = item
                if newpath in old_to_latest_map:
                    latestpath = old_to_latest_map[newpath]
                    latest_to_old_map[latestpath] = oldpath
                    latest_to_old_map[newpath] = oldpath
                    old_to_latest_map[oldpath] = latestpath
                else:
                    latest_to_old_map[newpath] = oldpath
                    old_to_latest_map[oldpath] = newpath
                new_history.append(item)
            else:
                assert("Unknown Type: " + str(type(item)))
        new_history.reverse()
        self.all_history = new_history

    def generate_git_repository(self):
        os.makedirs(self.outdir)
        oldcwd = os.getcwd()
        os.chdir(self.outdir)
        # git init
        self.execute(['git', 'init'], exception=True)
        # git config
        if self.name:
            self.execute(['git', 'config', 'user.name', self.name], exception=True)
        if self.email:
            self.execute(['git', 'config', 'user.email', self.email], exception=True)
        for item in self.all_history:
            if type(item) == Commit:
                self.commit(item)
            elif type(item) == Rename:
                self.rename(item)
            else:
                assert("Unknown Type: " + str(type(item)))
        self.copy_latests()
        os.chdir(oldcwd)

    def commit(self, commit):
        # !!! you must have ch(anged )dir to git repo when you use this function !!!
        date = datetime.utcfromtimestamp(commit.unixtime).isoformat()
        os.environ['GIT_COMMITTER_DATE'] = date
        os.environ['GIT_AUTHOR_DATE'] = date
        dirname = os.path.dirname(commit.path)
        if dirname and not os.path.exists(dirname):
            os.makedirs(dirname)
        with open(commit.path, 'w') as file:
            file.write(commit.data)
        # git add
        self.execute(['git', 'add', commit.path], exception=True)
        if self.repository_has_no_diff():
            return
        name, _ = os.path.splitext(commit.path)
        # git commit
        self.execute(['git', 'commit', '-m', name + ' (PukiWiki)'], exception=True)

    def rename(self, rename):
        # !!! you must have ch(anged )dir to git repo when you use this function !!!
        date = datetime.utcfromtimestamp(rename.unixtime).isoformat()
        os.environ['GIT_COMMITTER_DATE'] = date
        os.environ['GIT_AUTHOR_DATE'] = date
        # git mv
        if self.execute(['git', 'mv', rename.oldpath, rename.newpath]):
            return
        if self.repository_has_no_diff():
            return
        oldname, _ = os.path.splitext(rename.oldpath)
        newname, _ = os.path.splitext(rename.newpath)
        # git commit
        self.execute(['git', 'commit', '-m', oldname + ' -> ' + newname + ' (PukiWiki)'], exception=True)

    def copy_latests(self):
        # !!! you must have ch(anged )dir to git repo when you use this function !!!
        print("finalizing...")
        if 'GIT_COMMITTER_DATE' in os.environ:
            del os.environ['GIT_COMMITTER_DATE']
        if 'GIT_AUTHOR_DATE' in os.environ:
            del os.environ['GIT_AUTHOR_DATE']
        for rmpath in glob.iglob('**/*.txt', recursive=True):
            # git rm (wiki-repo/*)
            self.execute(['git', 'rm', rmpath], exception=True)
        pattern = os.path.join(self.basedir_abs, 'wiki/**/*.txt')
        prefixlen = len(os.path.join(self.basedir_abs, 'wiki') + os.sep)
        for oldpath in glob.iglob(pattern, recursive=True):
            newpath = oldpath[prefixlen:]
            dirname = os.path.dirname(newpath)
            if dirname and not os.path.exists(dirname):
                os.makedirs(dirname)
            shutil.copy(oldpath, newpath)
            # git add (wiki/*)
            self.execute(['git', 'add', newpath], exception=True)
        if self.repository_has_no_diff():
            return
        # git commit
        self.execute(['git', 'commit', '-m', 'migrated from PukiWiki using migpuki'], exception=True)

    def repository_has_no_diff(self):
        # !!! you must have ch(anged )dir to git repo when you use this function !!!
        # git diff-index
        # http://stackoverflow.com/questions/3878624/how-do-i-programmatically-determine-if-there-are-uncommited-changes
        return not self.execute(['git', 'diff-index', '--quiet', 'HEAD', '--'], silent=True)

    def printv(self, *args, **kwargs):
        if self.verbose:
            print(*args, **kwargs)

    def execute(self, command, *, silent=False, exception=False):
        proc = None
        if silent:
            proc = subprocess.run(command, stdout=subprocess.PIPE)
        else:
            proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        message = proc.stdout.decode('utf-8')
        if not silent:
            if proc.returncode != 0:
                print(message, end='')
            else:
                self.printv(message, end='')
        if proc.returncode != 0 and exception:
            raise Exception('failed: {}, return code: {}'.format(' '.join(command), proc.returncode))
        return proc.returncode

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='gitify PukiWiki data.')
    parser.add_argument('basedir',
                        help='UTF-8ized PukiWiki root directory (which has wiki / backup directories)')
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true', default=False,
                        help='show verbose log')
    parser.add_argument('-o', '--outdir', default='wiki-repo',
                        help='output directory name')
    parser.add_argument('-n', '--name', help='Git author / committer name')
    parser.add_argument('-e', '--email', help='Git author / committer email')
    parser.add_argument('-r', '--renamelog', dest='renamelog', action='store_true', default=False,
                        help='parse rename log and execute git mv (experimental)')
    params = parser.parse_args()

    gitify = Gitify(basedir=params.basedir,
                    verbose=params.verbose,
                    outdir=params.outdir,
                    name=params.name,
                    email=params.email,
                    renamelog=params.renamelog)
    gitify.run()
