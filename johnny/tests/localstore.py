#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for johnny-cache.  Much of johnny cache is designed to cache things
forever, and because it aims to keep coherency despite that it's important
that it be tested thoroughly to make sure no changes introduce the possibility
of stale data in the cache."""

from threading import Thread, current_thread
from time import sleep
from django.test import TestCase
from johnny import localstore, cache, middleware
from johnny.compat import Queue

class LocalStoreTest(TestCase):
    def test_basic_operation(self):
        store = localstore.LocalStore()
        for x in (1,2,3,4,5):
            store['key%s' % x] = "value%s" % x
        self.assertEqual(store.key3, "value3")
        self.assertEqual(store['key4'], "value4")
        self.assertEqual(len(store), 5)
        self.assertEqual(sorted(list(store)),
                          sorted(store.keys()))
        self.assertEqual(store.setdefault('key6', 'value6'), 'value6')
        self.assertEqual(store['key6'], 'value6')
        del store['key2']
        self.assertEqual(len(store), 5)
        store.clear()
        self.assertEqual(len(store), 0)

    def test_custom_clear(self):
        """Test that clear(glob) works as expected."""
        store = localstore.LocalStore()
        for x in (1,2,3,4,5):
            store['key_%s' % x] = 'value_%s' % x
            store['ex_%s' % x] = 'ecks_%s' % x
        self.assertEqual(len(store), 10)
        store.clear('*4')
        self.assertEqual(len(store), 8)
        store.clear('ex_*')
        self.assertEqual(len(store), 4)
        self.assertEqual(len(store.mget('key*')), 4)
        self.assertEqual(len(store.mget('*_2')), 1)

    def test_thread_locality(self):
        store = localstore.LocalStore()
        store['name'] = "Hi"
        q = Queue()
        def do_test():
            sleep(0.1)
            t = current_thread()
            name = t.name
            store[name] = 1
            store['name'] = name
            q.put(dict(store))
        threads = []
        for x in range(5):
            t = Thread(target=do_test, name='thread%x' % x)
            t.start()
            threads.append(t)
        for t in threads:
            t.join()
        # assert none of the thread stuff touched our queue
        self.assertEqual(store['name'], 'Hi')
        self.assertEqual(q.qsize(), 5)
        qcontents = []
        while not q.empty():
            qcontents.append(q.get())
        self.assertEqual(len(qcontents), 5)
        for d in qcontents:
            self.assertEqual(len(d), 2)
            self.assertNotEqual(d['name'], 'Hi')
            self.assertEqual(d[d['name']], 1)

    def test_localstore_clear_middleware(self):
        cache.local.clear()
        cache.local['eggs'] = 'spam'
        cache.local['charlie'] = 'chaplin'
        self.assertEqual(len(cache.local), 2)
        middleware.LocalStoreClearMiddleware().process_response(None, None)
        self.assertEqual(len(cache.local), 0)


