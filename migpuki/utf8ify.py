#!/usr/bin/env python3
# requirements: Python 3.5, nkf, gzip

import argparse
import codecs
import glob
import gzip as gziplib
import os
import os.path
import re
import shutil
import subprocess
import sys
import unicodedata
from collections import namedtuple

pathbadchars = {':'}
UTF8ifyConf = namedtuple('UTF8ifyConf', ['pattern', 'banset', 'gzip', 'convert'])

class UTF8ify:
    def __init__(self, basedir, *, verbose=False, outdir='utf8', encoding='euc_jp', noconvert=False, normalize_mode='NFC'):
        self.basedir = basedir
        self.verbose = verbose
        self.outdir = outdir
        self.encoding = encoding
        self.noconvert = noconvert
        self.normalize_mode = normalize_mode

    def run(self):
        confs = [
            UTF8ifyConf('wiki/**/*.txt', {r'/dir\.txt$'}, gzip=False, convert=True),
            UTF8ifyConf('backup/**/*.txt', {r'/dir\.txt$'}, gzip=False, convert=True),
            UTF8ifyConf('backup/**/*.gz', {}, gzip=True, convert=True),
            UTF8ifyConf('diff/**/*.txt', {r'/dir\.txt$'}, gzip=False, convert=True),
            UTF8ifyConf('counter/**/*.count', {}, gzip=False, convert=True),
            UTF8ifyConf('attach/**/*', {r'/dir\.txt$', r'\.log$'}, gzip=False, convert=False),
        ]
        for conf in confs:
            pattern = os.path.join(self.basedir, conf.pattern)
            banset = {re.compile(s) for s in conf.banset}
            for oldpath in glob.iglob(pattern, recursive=True):
                if os.path.isfile(oldpath):
                    banned = False
                    for ban_re in banset:
                        if ban_re.search(oldpath):
                            banned = True
                            break
                    if not banned:
                        self.utf8ify_file(oldpath, convert=conf.convert, gzip=conf.gzip)

    def utf8ify_file(self, oldpath: str, *, convert=False, gzip=False):
        if self.noconvert:
            convert = False
        newpath = self.generate_new_path(oldpath)
        self.printv('old: ' + oldpath)
        self.printv('new: ' + newpath)
        newdirname = os.path.dirname(newpath)
        if not os.path.exists(newdirname):
            os.makedirs(newdirname)
        if convert:
            try:
                openf = gziplib.open if gzip else open
                with openf(newpath, 'wb') as newfile:
                    with openf(oldpath, 'rb') as oldfile:
                        self.convert_stream(oldfile, newfile)
            except UnicodeError as e:
                print('Error: {} -> {} \n       {}'.format(oldpath, newpath, e), file=sys.stderr)
                with openf(newpath, 'wb') as newfile:
                    with openf(oldpath, 'rb') as oldfile:
                        self.convert_stream(oldfile, newfile, errors='replace')
                newnoextname, _ = os.path.splitext(os.path.basename(newpath))
                neweucpath = os.path.join(newdirname, newnoextname + "." + self.encoding)
                shutil.copy(oldpath, neweucpath)
                print('Copy:  {} -> {}'.format(oldpath, neweucpath), file=sys.stderr)
        else:
            shutil.copy(oldpath, newpath)

    def convert_stream(self, oldfile, newfile, *, errors='strict'):
        # FIXME: buffer?
        newfile.write(bytes(oldfile.read().decode(self.encoding, errors=errors), self.encoding, errors=errors))

    def generate_new_path(self, oldpath: str):
        olddirname = os.path.dirname(oldpath)
        oldbasename = os.path.basename(oldpath)
        oldnoextname, oldextname = os.path.splitext(oldbasename)
        oldparts = oldnoextname.split('_')
        newnoextname = None
        try:
            newparts = []
            for s in oldparts:
                euc = codecs.decode(s, 'hex_codec')
                utf8 = codecs.decode(euc, self.encoding)
                newparts.append(utf8)
            utf8name = '_'.join(newparts)
            newnoextname = unicodedata.normalize(self.normalize_mode, utf8name)
        except Exception as e:
            raise e  # FIXME
        for c in pathbadchars:
            newnoextname = newnoextname.replace(c, '_')
        newdirname = olddirname
        basedir = self.basedir
        if newdirname.startswith(basedir):
            newdirname = newdirname[len(basedir):]
            if newdirname.startswith(os.sep):
                newdirname = newdirname[1:]
        newpath = os.path.join(self.outdir, newdirname, newnoextname + oldextname)
        return newpath

    def printv(self, *args, **kwargs):
        if self.verbose:
            print(*args, **kwargs)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='UTF-8ify PukiWiki data.')
    parser.add_argument('basedir',
                        help='PukiWiki root directory (which has index.php)')
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true', default=False,
                        help='show verbose log')
    parser.add_argument('-o', '--outdir', default='utf8',
                        help='output directory name')
    parser.add_argument('-n', '--noconvert', dest='noconvert', action='store_true', default=False,
                        help='not convert text files between character encodings')
    parser.add_argument('-e', '--encoding', default='euc_jp',
                        help='encoding of PukiWiki data (euc_jp / utf_8) (tested euc_jp only)')
    # ref.) http://qiita.com/knaka/items/48e1799b56d520af6a09
    parser.add_argument('-u', '--normalize', default='NFC',
                        help='unicode normalize mode for filepath (NFC / NFD / NFKC / NFKD)')

    params = parser.parse_args()

    utf8ify = UTF8ify(basedir=params.basedir,
                      verbose=params.verbose,
                      outdir=params.outdir,
                      encoding=params.encoding,
                      noconvert=params.noconvert,
                      normalize_mode=params.normalize)
    utf8ify.run()
