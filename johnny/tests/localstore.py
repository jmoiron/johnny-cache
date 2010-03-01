#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for johnny-cache.  Much of johnny cache is designed to cache things
forever, and because it aims to keep coherency despite that it's important
that it be tested thoroughly to make sure no changes introduce the possibility
of stale data in the cache."""

from django.test import TestCase
from johnny import localstore

class LocalStoreTest(TestCase):
    def test_basic_operation(self):
        store = localstore.LocalStore()
        for x in (1,2,3,4,5):
            store['key%s' % x] = "value%s" % x
        self.assertEquals(store.key3, "value3")
        self.assertEquals(store['key4'], "value4")
        self.assertEquals(len(store), 5)
        self.assertEquals(sorted(list(store)),
                          sorted(store.keys()))
        self.assertEquals(store.setdefault('key6', 'value6'), 'value6')
        self.assertEquals(store['key6'], 'value6')
        del store['key2']
        self.assertEquals(len(store), 5)
        store.clear()
        self.assertEquals(len(store), 0)

    def test_custom_clear(self):
        """Test that clear(glob) works as expected."""
        store = localstore.LocalStore()
        for x in (1,2,3,4,5):
            store['key_%s' % x] = 'value_%s' % x
            store['ex_%s' % x] = 'ecks_%s' % x
        self.assertEquals(len(store), 10)
        store.clear('*4')
        self.assertEquals(len(store), 8)
        store.clear('ex_*')
        self.assertEquals(len(store), 4)
        self.assertEquals(len(store.mget('key*')), 4)
        self.assertEquals(len(store.mget('*_2')), 1)

    def test_thread_locality(self):
        from Queue import Queue
        try:
            from threading import Thread, current_thread
        except:
            #python 2.5 difference
            from threading import Thread
            from threading import currentThread as current_thread
        from time import sleep
        store = localstore.LocalStore()
        store['name'] = "Hi"
        q = Queue()
        def do_test():
            sleep(0.1)
            t = current_thread()
            try:
                name = t.name
            except AttributeError:
                #python 2.5 difference
                name = t.getName()
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
        self.assertEquals(store['name'], 'Hi')
        self.assertEquals(q.qsize(), 5)
        qcontents = []
        while not q.empty():
            qcontents.append(q.get())
        self.assertEquals(len(qcontents), 5)
        for d in qcontents:
            self.assertEquals(len(d), 2)
            self.assertNotEquals(d['name'], 'Hi')
            self.assertEquals(d[d['name']], 1)

    def test_localstore_clear_middleware(self):
        from johnny import cache, middleware
        cache.local.clear()
        cache.local['eggs'] = 'spam'
        cache.local['charlie'] = 'chaplin'
        self.failUnless(len(cache.local) == 2)
        middleware.LocalStoreClearMiddleware().process_response(None, None)
        self.failUnless(len(cache.local) == 0)


