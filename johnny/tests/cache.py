#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for the QueryCache functionality of johnny."""

from django.conf import settings
from django.db import connection
from johnny import middleware
import base

# put tests in here to be included in the testing suite
__all__ = ['MultiDbTest', 'SingleModelTest', 'MultiModelTest', 'TransactionSupportTest']

def _pre_setup(self):
    self.saved_DISABLE_SETTING = getattr(settings, 'DISABLE_QUERYSET_CACHE', False)
    settings.DISABLE_QUERYSET_CACHE = False
    self.middleware = middleware.QueryCacheMiddleware()

def _post_teardown(self):
    self.middleware.unpatch()
    settings.DISABLE_QUERYSET_CACHE = self.saved_DISABLE_SETTING

class QueryCacheBase(base.JohnnyTestCase):
    def _pre_setup(self):
        _pre_setup(self)
        super(QueryCacheBase, self)._pre_setup()

    def _post_teardown(self):
        _post_teardown(self)
        super(QueryCacheBase, self)._post_teardown()

class TransactionQueryCacheBase(base.TransactionJohnnyTestCase):
    def _pre_setup(self):
        _pre_setup(self)
        super(TransactionQueryCacheBase, self)._pre_setup()

    def _post_teardown(self):
        _post_teardown(self)
        super(TransactionQueryCacheBase, self)._post_teardown()


class MultiDbTest(TransactionQueryCacheBase):
    multi_db = True
    fixtures = ['genres.json', 'genres.second.json']

    def test_basic_queries(self):
        """Tests basic queries and that the cache is working for multiple db's"""
        from testapp.models import Genre, Book, Publisher, Person
        from django.db import connections
        if len(getattr(settings, "DATABASES", [])) <= 1:
            print "Skipping multi databases"
            return 
        self.failUnless("default" in getattr(settings, "DATABASES"))
        self.failUnless("second" in getattr(settings, "DATABASES"))

        g1 = Genre.objects.using("default").get(pk=1)
        g1.title = "A default database"
        g1.save()
        g2 = Genre.objects.using("second").get(pk=1)
        g2.title = "A second database"
        g2.save()
        for c in connections:
            connections[c].queries = []
        #fresh from cache since we saved each
        g1 = Genre.objects.using('default').get(pk=1)
        g2 = Genre.objects.using('second').get(pk=1)
        for c in connections:
            self.failUnless(len(connections[c].queries) == 1)
        self.failUnless(g1.title == "A default database")
        self.failUnless(g2.title == "A second database")
        #should be a cache hit
        g1 = Genre.objects.using('default').get(pk=1)
        g2 = Genre.objects.using('second').get(pk=1)
        for c in connections:
            self.failUnless(len(connections[c].queries) == 1)

    def test_transactions(self):
        """Tests transaction rollbacks and local cache for multiple dbs"""
        from testapp.models import Genre
        from django.db import connections, transaction
        if len(getattr(settings, "DATABASES", [])) <= 1:
            print "Skipping multi databases"
            return 
        self.failUnless("default" in getattr(settings, "DATABASES"))
        self.failUnless("second" in getattr(settings, "DATABASES"))

        g1 = Genre.objects.using("default").get(pk=1)
        start_g1 = g1.title
        g2 = Genre.objects.using("second").get(pk=1)

        transaction.enter_transaction_management(using='default')
        transaction.managed(using='default')
        transaction.enter_transaction_management(using='second')
        transaction.managed(using='second')

        g1.title = "Testing a rollback"
        g2.title = "Testing a commit"
        g1.save()
        g2.save()
        transaction.rollback(using='default')
        transaction.commit(using='second')
        connections['default'].queries = []
        connections['second'].queries = []
        #should not be a db hit due to rollback
        g1 = Genre.objects.using("default").get(pk=1)
        #should be a db hit due to commit
        g2 = Genre.objects.using("second").get(pk=1)
        self.failUnless(connections['default'].queries == [])
        self.failUnless(len(connections['second'].queries) == 1)

        self.failUnless(g1.title == start_g1)
        self.failUnless(g2.title == "Testing a commit")
        transaction.managed(False, "default")
        transaction.managed(False, "second")
        transaction.leave_transaction_management("default")
        transaction.leave_transaction_management("second")

    def test_savepoints(self):
        """tests savepoints for multiple db's"""
        from testapp.models import Genre
        from django.db import connections, transaction
        if len(getattr(settings, "DATABASES", [])) <= 1:
            print "Skipping multi databases"
            return 
        self.failUnless("default" in getattr(settings, "DATABASES"))
        self.failUnless("second" in getattr(settings, "DATABASES"))
        g1 = Genre.objects.using("default").get(pk=1)
        start_g1 = g1.title
        g2 = Genre.objects.using("second").get(pk=1)

        transaction.enter_transaction_management(using='default')
        transaction.managed(using='default')
        transaction.enter_transaction_management(using='second')
        transaction.managed(using='second')

        g1.title = "Rollback savepoint"
        g1.save()

        g2.title = "Commited savepoint"
        g2.save()
        sid2 = transaction.savepoint(using="second")

        sid = transaction.savepoint(using="default")
        g1.title = "Dirty text"
        g1.save()

        #should not be a hit due to rollback
        connections["default"].queries = []
        transaction.savepoint_rollback(sid, using="default")
        g1 = Genre.objects.using("default").get(pk=1)
        #self.failUnless(connections["default"].queries == [])
        self.failUnless(g1.title == start_g1)

        #will be pushed to dirty in commit
        g2 = Genre.objects.using("second").get(pk=1)
        self.failUnless(g2.title == "Commited savepoint")
        transaction.savepoint_commit(sid2, using="second")
        connections["second"].queries = []
        g2 = Genre.objects.using("second").get(pk=1)
        self.failUnless(connections["second"].queries == [])
        transaction.commit(using="second")
        g2 = Genre.objects.using("second").get(pk=1)
        self.failUnless(connections["second"].queries == [])
        self.failUnless(g2.title == "Commited savepoint")
        transaction.managed(False, "default")
        transaction.managed(False, "second")
        transaction.leave_transaction_management("default")
        transaction.leave_transaction_management("second")

        
class SingleModelTest(QueryCacheBase):
    fixtures = base.johnny_fixtures

    def test_basic_querycaching(self):
        """A basic test that querycaching is functioning properly and is
        being invalidated properly on singular table reads & writes."""
        from testapp.models import Publisher
        connection.queries = []
        starting_count = Publisher.objects.count()
        starting_count = Publisher.objects.count()
        # make sure that doing this twice doesn't hit the db twice
        self.failUnless(len(connection.queries) == 1)
        self.failUnless(starting_count == 1)
        # this write should invalidate the key we have
        Publisher(title='Harper Collins', slug='harper-collins').save()
        connection.queries = []
        new_count = Publisher.objects.count()
        self.failUnless(len(connection.queries) == 1)
        self.failUnless(new_count == 2)

    def test_querycache_return_results(self):
        """Test that the return results from the query cache are what we
        expect;  single items are single items, etc."""
        from testapp.models import Publisher
        connection.queries = []
        pub = Publisher.objects.get(id=1)
        pub2 = Publisher.objects.get(id=1)
        self.failUnless(pub == pub2)
        self.failUnless(len(connection.queries) == 1)
        pubs = list(Publisher.objects.all())
        pubs2 = list(Publisher.objects.all())
        self.failUnless(pubs == pubs2)
        self.failUnless(len(connection.queries) == 2)

    def test_queryset_laziness(self):
        """This test exists to model the laziness of our queries;  the
        QuerySet cache should not alter the laziness of QuerySets."""
        from testapp.models import Genre
        connection.queries = []
        qs = Genre.objects.filter(title__startswith='A')
        qs = qs.filter(pk__lte=1)
        qs = qs.order_by('pk')
        # we should only execute the query at this point
        arch = qs[0]
        self.failUnless(len(connection.queries) == 1)

    def test_order_by(self):
        """A basic test that our query caching is taking order clauses
        into account."""
        from testapp.models import Genre
        connection.queries = []
        first = list(Genre.objects.filter(title__startswith='A').order_by('slug'))
        second = list(Genre.objects.filter(title__startswith='A').order_by('-slug'))
        # test that we've indeed done two queries and that the orders
        # of the results are reversed
        self.failUnless((first[0], first[1] == second[1], second[0]))
        self.failUnless(len(connection.queries) == 2)

    def test_signals(self):
        """Test that the signals we say we're sending are being sent."""
        from testapp.models import Genre
        from johnny.signals import qc_hit, qc_miss
        connection.queries = []
        misses = []
        hits = []
        def qc_hit_listener(sender, **kwargs):
            hits.append(kwargs['key'])
        def qc_miss_listener(*args, **kwargs):
            misses.append(kwargs['key'])
        qc_hit.connect(qc_hit_listener)
        qc_miss.connect(qc_miss_listener)
        first = list(Genre.objects.filter(title__startswith='A').order_by('slug'))
        second = list(Genre.objects.filter(title__startswith='A').order_by('slug'))
        self.failUnless(len(misses) == len(hits) == 1)

class MultiModelTest(QueryCacheBase):
    fixtures = base.johnny_fixtures

    def test_foreign_keys(self):
        """Test that simple joining (and deferred loading) functions as we'd
        expect when involving multiple tables.  In particular, a query that
        joins 2 tables should invalidate when either table is invalidated."""
        from testapp.models import Genre, Book, Publisher, Person
        connection.queries = []
        books = list(Book.objects.select_related('publisher'))
        books = list(Book.objects.select_related('publisher'))
        str(books[0].genre)
        # this should all have done one query..
        self.failUnless(len(connection.queries) == 1)
        books = list(Book.objects.select_related('publisher'))
        # invalidate the genre key, which shouldn't impact the query
        Genre(title='Science Fiction', slug='scifi').save()
        after_save = len(connection.queries)
        books = list(Book.objects.select_related('publisher'))
        self.failUnless(len(connection.queries) == after_save)
        # now invalidate publisher, which _should_
        p = Publisher(title='McGraw Hill', slug='mcgraw-hill')
        p.save()
        after_save = len(connection.queries)
        books = list(Book.objects.select_related('publisher'))
        self.failUnless(len(connection.queries) == after_save + 1)
        # the query should be cached again... 
        books = list(Book.objects.select_related('publisher'))
        # this time, create a book and the query should again be uncached..
        Book(title='Anna Karenina', slug='anna-karenina', publisher=p).save()
        after_save = len(connection.queries)
        books = list(Book.objects.select_related('publisher'))
        self.failUnless(len(connection.queries) == after_save + 1)

    def test_invalidate(self):
        """Test for the module-level invalidation function."""
        from Queue import Queue as queue
        from testapp.models import Book, Genre, Publisher
        from johnny.cache import invalidate
        from johnny.signals import qc_hit, qc_miss
        q = queue()
        def hit(*args, **kwargs):
            q.put(True)
        def miss(*args, **kwargs):
            q.put(False)
        qc_hit.connect(hit)
        qc_miss.connect(miss)

        b = Book.objects.get(id=1)
        invalidate(Book)
        b = Book.objects.get(id=1)
        first, second = q.get(), q.get()
        self.failUnless(first == second == False)
        g = Genre.objects.get(id=1)
        p = Publisher.objects.get(id=1)
        invalidate('testapp_genre', Publisher)
        g = Genre.objects.get(id=1)
        p = Publisher.objects.get(id=1)
        fg,fp,sg,sp = [q.get() for i in range(4)]
        self.failUnless(fg == fp == sg == sp == False)

class TransactionSupportTest(TransactionQueryCacheBase):
    fixtures = base.johnny_fixtures

    def _run_threaded(self, query, queue):
        """Runs a query (as a string) from testapp in another thread and
        puts (hit?, result) on the provided queue."""
        from threading import Thread
        def _inner(_query):
            from testapp.models import Genre, Book, Publisher, Person
            from johnny.signals import qc_hit, qc_miss
            msg = []
            def hit(*args, **kwargs):
                msg.append(True)
            def miss(*args, **kwargs):
                msg.append(False)
            qc_hit.connect(hit)
            qc_miss.connect(miss)
            obj = eval(_query)
            msg.append(obj)
            queue.put(msg)
        t = Thread(target=_inner, args=(query,))
        t.start()
        t.join()

    def tearDown(self):
        from django.db import transaction
        if transaction.is_managed():
            if transaction.is_dirty():
                transaction.rollback()
            transaction.managed(False)
            transaction.leave_transaction_management()

    def test_transaction_commit(self):
        """Test transaction support in Johnny."""
        from Queue import Queue as queue
        from django.db import transaction
        from testapp.models import Genre, Publisher
        from johnny import cache

        self.failUnless(transaction.is_managed() == False)
        self.failUnless(transaction.is_dirty() == False)
        connection.queries = []
        cache.local.clear()
        q = queue()
        other = lambda x: self._run_threaded(x, q)

        # load some data
        start = Genre.objects.get(id=1)
        other('Genre.objects.get(id=1)')
        hit, ostart = q.get()
        # these should be the same and should have hit cache
        self.failUnless(hit)
        self.failUnless(ostart == start)
        # enter manual transaction management
        transaction.enter_transaction_management()
        transaction.managed()
        start.title = 'Jackie Chan Novels'
        # local invalidation, this key should hit the localstore!
        nowlen = len(cache.local)
        start.save()
        self.failUnless(nowlen != len(cache.local))
        # perform a read OUTSIDE this transaction... it should still see the
        # old gen key, and should still find the "old" data
        other('Genre.objects.get(id=1)')
        hit, ostart = q.get()
        self.failUnless(hit)
        self.failUnless(ostart.title != start.title)
        transaction.commit()
        # now that we commit, we push the localstore keys out;  this should be
        # a cache miss, because we never read it inside the previous transaction
        other('Genre.objects.get(id=1)')
        hit, ostart = q.get()
        self.failUnless(not hit)
        self.failUnless(ostart.title == start.title)
        transaction.managed(False)
        transaction.leave_transaction_management()

    def test_transaction_rollback(self):
        """Tests johnny's handling of transaction rollbacks.

        Similar to the commit, this sets up a write to a db in a transaction,
        reads from it (to force a cache write of sometime), then rolls back."""
        from Queue import Queue as queue
        from django.db import transaction
        from testapp.models import Genre, Publisher
        from johnny import cache

        self.failUnless(transaction.is_managed() == False)
        self.failUnless(transaction.is_dirty() == False)
        connection.queries = []
        cache.local.clear()
        q = queue()
        other = lambda x: self._run_threaded(x, q)

        # load some data
        start = Genre.objects.get(id=1)
        other('Genre.objects.get(id=1)')
        hit, ostart = q.get()
        # these should be the same and should have hit cache
        self.failUnless(hit)
        self.failUnless(ostart == start)
        # enter manual transaction management
        transaction.enter_transaction_management()
        transaction.managed()
        start.title = 'Jackie Chan Novels'
        # local invalidation, this key should hit the localstore!
        nowlen = len(cache.local)
        start.save()
        self.failUnless(nowlen != len(cache.local))
        # perform a read OUTSIDE this transaction... it should still see the
        # old gen key, and should still find the "old" data
        other('Genre.objects.get(id=1)')
        hit, ostart = q.get()
        self.failUnless(hit)
        self.failUnless(ostart.title != start.title)
        # perform a READ inside the transaction;  this should hit the localstore
        # but not the outside!
        nowlen = len(cache.local)
        start2 = Genre.objects.get(id=1)
        self.failUnless(start2.title == start.title)
        self.failUnless(len(cache.local) > nowlen)
        transaction.rollback()
        # we rollback, and flush all johnny keys related to this transaction
        # subsequent gets should STILL hit the cache in the other thread
        # and indeed, in this thread.

        self.failUnless(transaction.is_dirty() == False)
        other('Genre.objects.get(id=1)')
        hit, ostart = q.get()
        self.failUnless(hit)
        start = Genre.objects.get(id=1)
        self.failUnless(ostart.title == start.title)
        transaction.managed(False)
        transaction.leave_transaction_management()

    def test_savepoint_rollback(self):
        """Tests rollbacks of savepoints"""
        from django.db import transaction
        from testapp.models import Genre, Publisher
        from johnny import cache
        if not connection.features.uses_savepoints:
            return
        self.failUnless(transaction.is_managed() == False)
        self.failUnless(transaction.is_dirty() == False)
        connection.queries = []
        cache.local.clear()
        transaction.enter_transaction_management()
        transaction.managed()
        g = Genre.objects.get(pk=1)
        start_title = g.title
        g.title = "Adventures in Savepoint World"
        g.save()
        g = Genre.objects.get(pk=1)
        self.failUnless(g.title == "Adventures in Savepoint World")
        sid = transaction.savepoint()
        g.title = "In the Void"
        g.save()
        g = Genre.objects.get(pk=1)
        self.failUnless(g.title == "In the Void")
        transaction.savepoint_rollback(sid)
        g = Genre.objects.get(pk=1)
        self.failUnless(g.title == "Adventures in Savepoint World")
        transaction.rollback()
        g = Genre.objects.get(pk=1)
        self.failUnless(g.title == start_title)
        transaction.managed(False)
        transaction.leave_transaction_management()

    def test_savepoint_commit(self):
        """Tests a transaction commit (release)
        The release actually pushes the savepoint back into the dirty stack,
        but at the point it was saved in the transaction"""
        from django.db import transaction
        from testapp.models import Genre, Publisher
        from johnny import cache
        if not connection.features.uses_savepoints:
            return
        self.failUnless(transaction.is_managed() == False)
        self.failUnless(transaction.is_dirty() == False)
        connection.queries = []
        cache.local.clear()
        transaction.enter_transaction_management()
        transaction.managed()
        g = Genre.objects.get(pk=1)
        start_title = g.title
        g.title = "Adventures in Savepoint World"
        g.save()
        g = Genre.objects.get(pk=1)
        self.failUnless(g.title == "Adventures in Savepoint World")
        sid = transaction.savepoint()
        g.title = "In the Void"
        g.save()
        connection.queries = []
        #should be a database hit because of save in savepoint
        g = Genre.objects.get(pk=1)
        self.failUnless(len(connection.queries) == 1)
        self.failUnless(g.title == "In the Void")
        transaction.savepoint_commit(sid)
        #should be a cache hit against the dirty store
        connection.queries = []
        g = Genre.objects.get(pk=1)
        self.failUnless(connection.queries == [])
        self.failUnless(g.title == "In the Void")
        transaction.commit()
        #should have been pushed up to cache store
        g = Genre.objects.get(pk=1)
        self.failUnless(connection.queries == [])
        self.failUnless(g.title == "In the Void")
        transaction.managed(False)
        transaction.leave_transaction_management()
