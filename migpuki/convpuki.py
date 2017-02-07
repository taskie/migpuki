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

ConvPukiConf = namedtuple('ConvPukiConf', ['pattern', 'excludes', 'gzip', 'fileconv', 'pathconv'])
pathbadchars = {':'}
encoding_alias_map = {
    'euc_jp': {'eucjp', 'euc-jp'},
    'utf-8': {'utf8', 'utf_8'},
}
valid_encodings = {'euc_jp', 'utf-8'}
valid_normalizations = {'NFC', 'NFD', 'NFKC', 'NFKD'}

class ConvPuki:
    def __init__(self, basedir, *,
                 verbose=False, outdir='pukiwiki-conv', encoding_from='euc_jp', encoding_to='utf-8',
                 fileconv=True, pathconv=True, outhexpath=False, normalization='NFC'):
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
        for encoding, aliases in encoding_alias_map.items():
            if self.encoding_from.lower() in aliases:
                self.encoding_from = encoding
            if self.encoding_to.lower() in aliases:
                self.encoding_to = encoding
        if not self.pathconv and self.outhexpath:
            raise ValueError('you cannot set both of nopathconv and outhexpath')
        if self.encoding_from not in valid_encodings:
            raise ValueError('invalid encoding (from): ' + self.encoding_from)
        if self.encoding_to not in valid_encodings:
            raise ValueError('invalid encoding (to): ' + self.encoding_to)
        if self.normalization not in valid_normalizations:
            raise ValueError('invalid normalization mode: ' + self.normalization)
        if not self.outhexpath and self.encoding_to != 'utf-8':
            raise ValueError('you must set --outhexpath (-x) when you specify --encoding_to euc_jp' + self.normalization)

    def run(self):
        confs = [
            ConvPukiConf('wiki/**/*.txt', {r'/dir\.txt$'}, gzip=False, fileconv=True, pathconv=True),
            ConvPukiConf('backup/**/*.txt', {r'/dir\.txt$'}, gzip=False, fileconv=True, pathconv=True),
            ConvPukiConf('backup/**/*.gz', {}, gzip=True, fileconv=True, pathconv=True),
            ConvPukiConf('diff/**/*.txt', {r'/dir\.txt$'}, gzip=False, fileconv=True, pathconv=True),
            ConvPukiConf('counter/**/*.count', {}, gzip=False, fileconv=True, pathconv=True),
            ConvPukiConf('cache/**/*', {r'\.(?:re[fl]|tmp)$', r'/autolink\.dat$'}, gzip=False, fileconv=True, pathconv=False),
            ConvPukiConf('attach/**/*', {r'/dir\.txt$', r'\.log$'}, gzip=False, fileconv=False, pathconv=True),
        ]
        for conf in confs:
            print('* converting {} ...'.format(conf.pattern))
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
                        fileconv = False if not self.fileconv else conf.fileconv
                        pathconv = False if not self.pathconv else conf.pathconv
                        self.convpuki_file(oldpath, gzip=conf.gzip, fileconv=fileconv, pathconv=pathconv)

    def convpuki_file(self, oldpath: str, *, gzip=False, fileconv=False, pathconv=True):
        newpath = self.generate_new_path(oldpath, pathconv=pathconv)
        self.printv('--')
        self.printv('[old]: ' + oldpath)
        self.printv('[new]: ' + newpath)
        newdirname = os.path.dirname(newpath)
        if not os.path.exists(newdirname):
            os.makedirs(newdirname)
        if not fileconv or self.encoding_from == self.encoding_to:
            shutil.copy(oldpath, newpath)
            self.printv('[copy]: succeeded.')
        else:
            try:
                openf = gziplib.open if gzip else open
                with openf(newpath, 'wb') as newfile:
                    with openf(oldpath, 'rb') as oldfile:
                        self.fileconv_stream(oldfile, newfile)
                self.printv('[convert] succeeded.')
            except UnicodeError as e:
                print('[error]: {} -> {} \n{}'.format(oldpath, newpath, e), file=sys.stderr)
                with openf(newpath, 'wb') as newfile:
                    with openf(oldpath, 'rb') as oldfile:
                        self.fileconv_stream(oldfile, newfile, errors='replace')
                newrawpath = newpath + '.' + self.encoding_from
                shutil.copy(oldpath, newrawpath)
                print('[copy]: {} -> {}'.format(oldpath, newrawpath), file=sys.stderr)
                print('')

    def fileconv_stream(self, oldfile, newfile, *, errors='strict'):
        # FIXME: should use I/O stream
        decoded = oldfile.read().decode(self.encoding_from, errors=errors)
        newfile.write(decoded.encode(self.encoding_to, errors=errors))

    def generate_new_path(self, oldpath: str, pathconv=True):
        olddirname = os.path.dirname(oldpath)
        oldbasename = os.path.basename(oldpath)
        oldnoextname, oldextname = os.path.splitext(oldbasename)
        oldparts = oldnoextname.split('_')
        newnoextname = None
        if pathconv:
            try:
                newparts = []
                for s in oldparts:
                    b = codecs.decode(s, 'hex')
                    s = b.decode(self.encoding_from)
                    if self.outhexpath:
                        b = s.encode(self.encoding_to)
                        b = codecs.encode(b, 'hex')
                        s = codecs.decode(b, 'ascii').upper()
                    newparts.append(s)
                newnoextname = '_'.join(newparts)
                if self.encoding_to == 'utf-8':
                    newnoextname = unicodedata.normalize(self.normalization, newnoextname)
            except Exception as e:
                print('Error: ' + oldpath, file=sys.stderr)
                raise e
        else:
            newnoextname = oldnoextname
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
    parser = argparse.ArgumentParser(description='PukiWiki encoding converter')
    parser.add_argument('basedir',
                        help='PukiWiki root directory (which has index.php)')
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true', default=False,
                        help='show verbose log')
    parser.add_argument('-o', '--outdir', default='pukiwiki-conv',
                        help='output directory name (default: pukiwiki-conv)')
    parser.add_argument('-f', '--encoding_from', default='euc_jp',
                        help='input encoding of PukiWiki data: euc_jp (default) or utf-8')
    parser.add_argument('-t', '--encoding_to', default='utf-8',
                        help='output encoding of PukiWiki data: utf-8 (default) or euc_jp')
    parser.add_argument('-C', '--fileconv', dest='fileconv', action='store_true', default=True,
                        help='convert text files between character encodings (default: ON)')
    parser.add_argument('-c', '--nofileconv', dest='fileconv', action='store_false', default=False,
                        help='NOT convert text files between character encodings')
    parser.add_argument('-P', '--pathconv', dest='pathconv', action='store_true', default=True,
                        help='convert file paths from hex to <encoding_to> (default: ON)')
    parser.add_argument('-p', '--nopathconv', dest='pathconv', action='store_false', default=False,
                        help='NOT convert file paths from hex to <encoding_to>')
    parser.add_argument('-x', '--outhexpath', dest='outhexpath', action='store_true', default=False,
                        help='convert file paths from hex (<encoding_from>) to hex (<encoding_to>)')
    # ref.) http://qiita.com/knaka/items/48e1799b56d520af6a09
    parser.add_argument('-u', '--normalization', default='NFC',
                        help='unicode normalization mode for file paths: NFC (default), NFD, NFKC or NFKD')
    params = parser.parse_args()

    convpuki = ConvPuki(**vars(params))
    convpuki.run()

if __name__ == '__main__':
    main()
