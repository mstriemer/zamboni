from functools import partial
import os
import tempfile
import unittest

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage as storage

from nose.tools import eq_

from mkt.site.storage_utils import (walk_storage, copy_stored_file,
                                    move_stored_file)
from mkt.site.utils import rm_local_tmp_dir


def test_storage_walk():
    tmp = tempfile.mkdtemp()
    jn = partial(os.path.join, tmp)
    try:
        storage.save(jn('file1.txt'), ContentFile(''))
        storage.save(jn('one/file1.txt'), ContentFile(''))
        storage.save(jn('one/file2.txt'), ContentFile(''))
        storage.save(jn('one/two/file1.txt'), ContentFile(''))
        storage.save(jn('one/three/file1.txt'), ContentFile(''))
        storage.save(jn('four/five/file1.txt'), ContentFile(''))
        storage.save(jn(u'four/kristi\u2603/kristi\u2603.txt'),
                     ContentFile(''))

        results = [(dir, set(subdirs), set(files))
                   for dir, subdirs, files in sorted(walk_storage(tmp))]

        yield (eq_, results.pop(0),
               (tmp, set(['four', 'one']), set(['file1.txt'])))
        yield (eq_, results.pop(0),
               (jn('four'), set(['five', 'kristi\xe2\x98\x83']), set([])))
        yield (eq_, results.pop(0),
               (jn('four/five'), set([]), set(['file1.txt'])))
        yield (eq_, results.pop(0),
               (jn('four/kristi\xe2\x98\x83'), set([]),
                set(['kristi\xe2\x98\x83.txt'])))
        yield (eq_, results.pop(0),
               (jn('one'), set(['three', 'two']),
                set(['file1.txt', 'file2.txt'])))
        yield (eq_, results.pop(0),
               (jn('one/three'), set([]), set(['file1.txt'])))
        yield (eq_, results.pop(0),
               (jn('one/two'), set([]), set(['file1.txt'])))
        yield (eq_, len(results), 0)
    finally:
        rm_local_tmp_dir(tmp)


class TestFileOps(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        rm_local_tmp_dir(self.tmp)

    def path(self, path):
        return os.path.join(self.tmp, path)

    def contents(self, path):
        with storage.open(path, 'rb') as fp:
            return fp.read()

    def newfile(self, name, contents):
        src = self.path(name)
        storage.save(src, ContentFile(contents))
        return src

    def test_copy(self):
        src = self.newfile('src.txt', '<contents>')
        dest = self.path('somedir/dest.txt')
        copy_stored_file(src, dest)
        eq_(self.contents(dest), '<contents>')

    def test_self_copy(self):
        src = self.newfile('src.txt', '<contents>')
        dest = self.path('src.txt')
        copy_stored_file(src, dest)
        eq_(self.contents(dest), '<contents>')

    def test_move(self):
        src = self.newfile('src.txt', '<contents>')
        dest = self.path('somedir/dest.txt')
        move_stored_file(src, dest)
        eq_(self.contents(dest), '<contents>')
        eq_(storage.exists(src), False)

    def test_non_ascii(self):
        src = self.newfile(u'kristi\u0107.txt',
                           u'ivan kristi\u0107'.encode('utf8'))
        dest = self.path(u'somedir/kristi\u0107.txt')
        copy_stored_file(src, dest)
        eq_(self.contents(dest), 'ivan kristi\xc4\x87')

    def test_copy_chunking(self):
        src = self.newfile('src.txt', '<contents>')
        dest = self.path('somedir/dest.txt')
        copy_stored_file(src, dest, chunk_size=1)
        eq_(self.contents(dest), '<contents>')

    def test_move_chunking(self):
        src = self.newfile('src.txt', '<contents>')
        dest = self.path('somedir/dest.txt')
        move_stored_file(src, dest, chunk_size=1)
        eq_(self.contents(dest), '<contents>')
        eq_(storage.exists(src), False)
