#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for the QueryCache functionality of johnny."""

from django.conf import settings
from django.db import connection
from johnny import middleware
import base

# put tests in here to be included in the testing suite
__all__ = ['SingleModelTest', 'MultiModelTest', 'TransactionSupportTest']

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
        books = list(Book.objects.select_related('publisher'))
        self.failUnless(len(connection.queries) == 2)
        # now invalidate publisher, which _should_
        p = Publisher(title='McGraw Hill', slug='mcgraw-hill')
        p.save()
        books = list(Book.objects.select_related('publisher'))
        self.failUnless(len(connection.queries) == 4)
        # the query should be cached again... 
        books = list(Book.objects.select_related('publisher'))
        # this time, create a book and the query should again be uncached..
        Book(title='Anna Karenina', slug='anna-karenina', publisher=p).save()
        books = list(Book.objects.select_related('publisher'))
        self.failUnless(len(connection.queries) == 6)

class TransactionSupportTest(TransactionQueryCacheBase):
    fixtures = base.johnny_fixtures

    def test_local_transaction_hiding(self):
        """Test transaction support in Johnny."""
        from Queue import Queue as queue
        from threading import Thread

        from django.db import transaction
        from testapp.models import Genre, Publisher
        from johnny import cache
        self.failUnless(transaction.is_managed() == False)
        self.failUnless(transaction.is_dirty() == False)
        connection.queries = []
        cache.local.clear()
        q = queue()
        def other(query):
            """Executes an orm query as a string syncronously in another thread
            and puts the result on the q."""
            def _inner(que):
                from testapp.models import Genre, Publisher
                q.put(eval(que))
            t = Thread(target=_inner, args=(query,))
            t.start()
            t.join()

        # load some data
        start = Genre.objects.get(id=1)
        other('Genre.objects.get(id=1)')
        ostart = q.get()
        # so far so good, these should be the same and should have hit cache
        self.failUnless(len(connection.queries) == 1)
        self.failUnless(ostart == start)
        # enter manual transaction management
        transaction.enter_transaction_management()
        transaction.managed()

        start.name = 'Jackie Chan Novels'
        # local invalidation, this key should hit the localstore!
        nowlen = len(cache.local)
        start.save()
        self.failUnless(nowlen != len(cache.local))
        # perform a read OUTSIDE this transaction... it should still see the
        # old gen key, and should still find the right 
        other('Genre.objects.get(id=1)')
        ostart = q.get()
        self.failUnless(ostart.name != start.name)
        self.failUnless(len(connection.queries) == 2)
        transaction.commit()
        # now that we commit, we push the localstore keys out;  this should be
        # a cache miss, because we never read it inside the previous transaction
        other('Genre.objects.get(id=1)')
        ostart = q.get()
        self.failUnless(ostart.name == start.name)
        self.failUnless(len(connection.queries) == 3)
        transaction.leave_transaction_management()
