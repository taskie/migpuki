#!/usr/bin/env python3
# requirements: Python 3.5

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

UTF8ifyConf = namedtuple('UTF8ifyConf', ['pattern', 'excludes', 'gzip', 'fileconv', 'pathconv'])
pathbadchars = {':'}
valid_encodings = {'euc_jp', 'utf_8'}
valid_normalizations = {'NFC', 'NFD', 'NFKC', 'NFKD'}

class UTF8ify:
    def __init__(self, basedir, *,
                 verbose=False, outdir='utf8', encoding_from='euc_jp', encoding_to='utf_8',
                 fileconv=False, pathconv=False, outhexpath=True, normalization='NFC'):
        self.basedir = basedir
        self.verbose = verbose
        self.outdir = outdir
        self.encoding_from = encoding_from
        self.encoding_to = encoding_to
        self.fileconv = fileconv
        self.pathconv = pathconv
        self.outhexpath = outhexpath
        self.normalization = normalization
        self.validate()

    def validate(self):
        if not self.pathconv and self.outhexpath:
            raise ValueError('you cannot set both of nopathconv and outhexpath')
        if self.encoding_from not in valid_encodings:
            raise ValueError('invalid encoding (from): ' + self.encoding_from)
        if self.encoding_to not in valid_encodings:
            raise ValueError('invalid encoding (to): ' + self.encoding_to)
        if self.encoding_to not in valid_normalizations:
            raise ValueError('invalid normalization mode: ' + self.normalization)

    def run(self):
        confs = [
            UTF8ifyConf('wiki/**/*.txt', {r'/dir\.txt$'}, gzip=False, fileconv=True, pathconv=True),
            UTF8ifyConf('backup/**/*.txt', {r'/dir\.txt$'}, gzip=False, fileconv=True, pathconv=True),
            UTF8ifyConf('backup/**/*.gz', {}, gzip=True, fileconv=True, pathconv=True),
            UTF8ifyConf('diff/**/*.txt', {r'/dir\.txt$'}, gzip=False, fileconv=True, pathconv=True),
            UTF8ifyConf('counter/**/*.count', {}, gzip=False, fileconv=True, pathconv=True),
            UTF8ifyConf('cache/**/*', {r'\.re[fl]$'}, gzip=False, fileconv=True, pathconv=False),
            UTF8ifyConf('cache/**/*', {r'\.(dat|lock)$'}, gzip=False, fileconv=True, pathconv=True),
            UTF8ifyConf('attach/**/*', {r'/dir\.txt$', r'\.log$'}, gzip=False, fileconv=False, pathconv=True),
        ]
        for conf in confs:
            pattern = os.path.join(self.basedir, conf.pattern)
            excludes = {re.compile(s) for s in conf.excludes}
            for oldpath in glob.iglob(pattern, recursive=True):
                if os.path.isfile(oldpath):
                    banned = False
                    for exclude_re in excludes:
                        if exclude_re.search(oldpath):
                            banned = True
                            break
                    if not banned:
                        self.utf8ify_file(oldpath, fileconv=conf.fileconv, gzip=conf.gzip)

    def utf8ify_file(self, oldpath: str, *, gzip=False, fileconv=False, pathconv=True):
        if not self.fileconv:
            fileconv = False
        newpath = self.generate_new_path(oldpath, pathconv=pathconv)
        self.printv('--')
        self.printv('old: ' + oldpath)
        self.printv('new: ' + newpath)
        newdirname = os.path.dirname(newpath)
        if not os.path.exists(newdirname):
            os.makedirs(newdirname)
        if fileconv:
            try:
                openf = gziplib.open if gzip else open
                with openf(newpath, 'wb') as newfile:
                    with openf(oldpath, 'rb') as oldfile:
                        self.fileconv_stream(oldfile, newfile)
            except UnicodeError as e:
                print('error: {} -> {} \n       {}'.format(oldpath, newpath, e), file=sys.stderr)
                with openf(newpath, 'wb') as newfile:
                    with openf(oldpath, 'rb') as oldfile:
                        self.fileconv_stream(oldfile, newfile, errors='replace')
                newnoextname, _ = os.path.splitext(os.path.basename(newpath))
                newrawpath = os.path.join(newdirname, newnoextname + '.' + self.encoding_from)
                shutil.copy(oldpath, newrawpath)
                print('copy: {} -> {}'.format(oldpath, neweucpath), file=sys.stderr)
        else:
            shutil.copy(oldpath, newpath)

    def fileconv_stream(self, oldfile, newfile, *, errors='strict'):
        # FIXME: buffer?
        decoded = oldfile.read().decode(self.encoding_from, errors=errors)
        newfile.write(bytes(decoded, self.encoding_to, errors=errors))

    def generate_new_path(self, oldpath: str, pathconv=True):
        olddirname = os.path.dirname(oldpath)
        oldbasename = os.path.basename(oldpath)
        oldnoextname, oldextname = os.path.splitext(oldbasename)
        oldparts = oldnoextname.split('_')
        newnoextname = None
        try:
            newparts = []
            for s in oldparts:
                euc = codecs.decode(s, 'hex_codec')
                utf8 = codecs.decode(euc, self.encoding_from)
                newparts.append(utf8)
            utf8name = '_'.join(newparts)
            newnoextname = unicodedata.normalize(self.normalization, utf8name)
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

def main():
    parser = argparse.ArgumentParser(description='UTF-8ify PukiWiki data.')
    parser.add_argument('basedir',
                        help='PukiWiki root directory (which has index.php)')
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true', default=False,
                        help='show verbose log')
    parser.add_argument('-o', '--outdir', default='utf8',
                        help='output directory name')
    parser.add_argument('-f', '--encoding_from', default='euc_jp',
                        help='input encoding of PukiWiki data (euc_jp / utf_8) (tested euc_jp only)')
    parser.add_argument('-t', '--encoding_to', default='utf_8',
                        help='output encoding of PukiWiki data (utf_8 / euc_jp) (tested utf_8 only)')
    parser.add_argument('-c', '--fileconv', dest='fileconv', action='store_true', default=True,
                        help='convert text files between character encodings (default: ON)')
    parser.add_argument('-C', '--nofileconv', dest='fileconv', action='store_false', default=False,
                        help='NOT convert text files between character encodings')
    parser.add_argument('-p', '--pathconv', dest='pathconv', action='store_true', default=True,
                        help='convert file paths from hex_codec to <encoding_to> (default: ON)')
    parser.add_argument('-P', '--nopathconv', dest='pathconv', action='store_false', default=False,
                        help='NOT convert file paths from hex_codec to <encoding_to>')
    parser.add_argument('-h', '--outhexpath', dest='outhexpath', action='store_true', default=False,
                        help='convert file paths from hex_codec (<encoding_from>) to hex_codec (<encoding_to>)')
    # ref.) http://qiita.com/knaka/items/48e1799b56d520af6a09
    parser.add_argument('-u', '--normalization', default='NFC',
                        help='unicode normalization mode for file paths (NFC / NFD / NFKC / NFKD) (default: NFC)')
    params = parser.parse_args()

    utf8ify = UTF8ify(**vars(params))
    utf8ify.run()

if __name__ == '__main__':
    main()
