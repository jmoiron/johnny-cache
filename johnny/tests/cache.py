#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for the QueryCache functionality of johnny."""

import django
from django.conf import settings
from django.db import connection
try:
    from django.db import connections
except:
    connections = None
from johnny import middleware
from johnny import settings as johnny_settings
import base

try:
    any
except NameError:
    def any(iterable):
        for i in iterable:
            if i: return True
        return False

# put tests in here to be included in the testing suite
__all__ = ['MultiDbTest', 'SingleModelTest', 'MultiModelTest', 'TransactionSupportTest', 'BlackListTest', 'TransactionManagerTestCase', 'ParamsClashBug']

def _pre_setup(self):
    self.saved_DISABLE_SETTING = getattr(johnny_settings, 'DISABLE_QUERYSET_CACHE', False)
    johnny_settings.DISABLE_QUERYSET_CACHE = False
    self.middleware = middleware.QueryCacheMiddleware()

def _post_teardown(self):
    self.middleware.unpatch()
    johnny_settings.DISABLE_QUERYSET_CACHE = self.saved_DISABLE_SETTING

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
        from django.db import transaction
        _post_teardown(self)
        super(TransactionQueryCacheBase, self)._post_teardown()
        if transaction.is_managed():
            transaction.managed(False)

class BlackListTest(QueryCacheBase):
    fixtures = base.johnny_fixtures

    def test_basic_blacklist(self):
        from johnny import cache, settings
        from testapp.models import Genre, Book
        q = base.message_queue()
        old = johnny_settings.BLACKLIST
        johnny_settings.BLACKLIST = set(['testapp_genre'])
        connection.queries = []
        Book.objects.get(id=1)
        Book.objects.get(id=1)
        self.failUnless((False, True) == (q.get_nowait(), q.get_nowait()))
        list(Genre.objects.all())
        list(Genre.objects.all())
        self.failUnless(not any((q.get_nowait(), q.get_nowait())))
        johnny_settings.BLACKLIST = old


class MultiDbTest(TransactionQueryCacheBase):
    multi_db = True
    fixtures = ['genres.json', 'genres.second.json']

    def _run_threaded(self, query, queue):
        """Runs a query (as a string) from testapp in another thread and
        puts (hit?, result) on the provided queue."""
        from threading import Thread
        def _inner(_query):
            from testapp.models import Genre, Book, Publisher, Person
            from johnny.signals import qc_hit, qc_miss, qc_skip
            from johnny.cache import local
            from django.db import transaction
            msg = []
            def hit(*args, **kwargs):
                msg.append(True)
            def miss(*args, **kwargs):
                msg.append(False)
            def skip(*args, **kwargs):
                msg.append(False)
            qc_hit.connect(hit)
            qc_miss.connect(miss)
            qc_skip.connect(skip)
            obj = eval(_query)
            msg.append(obj)
            queue.put(msg)
        t = Thread(target=_inner, args=(query,))
        t.start()
        t.join()

    def _other(self, cmd, q):
        def _innter(cmd):
            q.put(eval(cmd))
        t = Thread(target=_inner, args=(cmd,))
        t.start()
        t.join()

    def test_basic_queries(self):
        """Tests basic queries and that the cache is working for multiple db's"""
        if len(getattr(settings, "DATABASES", [])) <= 1:
            print "\n  Skipping multi database tests"
            return

        from pprint import pformat
        from testapp.models import Genre, Book, Publisher, Person
        from django.db import connections

        self.failUnless("default" in getattr(settings, "DATABASES"))
        self.failUnless("second" in getattr(settings, "DATABASES"))

        g1 = Genre.objects.using("default").get(pk=1)
        g1.title = "A default database"
        g1.save(using='default')
        g2 = Genre.objects.using("second").get(pk=1)
        g2.title = "A second database"
        g2.save(using='second')
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

    def test_cache_key_setting(self):
        """Tests that two databases use a single cached object when given the same DB cache key"""
        if len(getattr(settings, "DATABASES", [])) <= 1:
            print "\n  Skipping multi database tests"
            return

        from testapp.models import Genre
        from django.db import connections

        self.failUnless("default" in getattr(settings, "DATABASES"))
        self.failUnless("second" in getattr(settings, "DATABASES"))

        old_cache_keys = johnny_settings.DB_CACHE_KEYS
        johnny_settings.DB_CACHE_KEYS = {'default': 'default', 'second': 'default'}

        g1 = Genre.objects.using("default").get(pk=1)
        g1.title = "A default database"
        g1.save(using='default')
        g2 = Genre.objects.using("second").get(pk=1)
        g2.title = "A second database"
        g2.save(using='second')
        for c in connections:
            connections[c].queries = []
        #fresh from cache since we saved each
        g1 = Genre.objects.using('default').get(pk=1)
        g2 = Genre.objects.using('second').get(pk=1)
        johnny_settings.DB_CACHE_KEYS = old_cache_keys
        total_queries = sum([len(connections[c].queries)
                             for c in connections])
        self.assertEqual(total_queries, 1)

    def test_transactions(self):
        """Tests transaction rollbacks and local cache for multiple dbs"""

        if len(getattr(settings, "DATABASES", [])) <= 1:
            print "\n  Skipping multi database tests"
            return
        if hasattr(settings, 'DATABASE_ENGINE'):
            if settings.DATABASE_ENGINE == 'sqlite3':
                print "\n  Skipping test requiring multiple threads."
                return
        else:
            from django.db import connections, transaction
            for db in settings.DATABASES.values():
                if db['ENGINE'] == 'sqlite3':
                    print "\n  Skipping test requiring multiple threads."
                    return

            for conname in connections:
                con = connections[conname]
                if not base.supports_transactions(con):
                    print "\n  Skipping test requiring transactions."
                    return

        from django.db import connections, transaction
        from johnny import cache as c
        from Queue import Queue as queue
        q = queue()
        other = lambda x: self._run_threaded(x, q)

        from testapp.models import Genre


        # sanity check 
        self.failUnless(transaction.is_managed() == False)
        self.failUnless(transaction.is_dirty() == False)
        self.failUnless("default" in getattr(settings, "DATABASES"))
        self.failUnless("second" in getattr(settings, "DATABASES"))

        # this should seed this fetch in the global cache
        g1 = Genre.objects.using("default").get(pk=1)
        g2 = Genre.objects.using("second").get(pk=1)
        start_g1 = g1.title

        transaction.enter_transaction_management(using='default')
        transaction.managed(using='default')
        transaction.enter_transaction_management(using='second')
        transaction.managed(using='second')

        g1.title = "Testing a rollback"
        g2.title = "Testing a commit"
        g1.save()
        g2.save()

        # test outside of transaction, should be cache hit and 
        # not contain the local changes
        other("Genre.objects.using('default').get(pk=1)")
        hit, ostart = q.get()
        self.failUnless(ostart.title == start_g1)
        self.failUnless(hit)

        transaction.rollback(using='default')
        transaction.commit(using='second')
        transaction.managed(False, "default")
        transaction.managed(False, "second")

        #other thread should have seen rollback
        other("Genre.objects.using('default').get(pk=1)")
        hit, ostart = q.get()
        self.failUnless(ostart.title == start_g1)
        self.failUnless(hit)

        connections['default'].queries = []
        connections['second'].queries = []
        #should be a cache hit due to rollback
        g1 = Genre.objects.using("default").get(pk=1)
        #should be a db hit due to commit
        g2 = Genre.objects.using("second").get(pk=1)
        self.failUnless(connections['default'].queries == [])
        self.failUnless(len(connections['second'].queries) == 1)

        #other thread sould now be accessing the cache after the get
        #from the commit.
        other("Genre.objects.using('second').get(pk=1)")
        hit, ostart = q.get()
        self.failUnless(ostart.title == g2.title)
        self.failUnless(hit)

        self.failUnless(g1.title == start_g1)
        self.failUnless(g2.title == "Testing a commit")
        transaction.leave_transaction_management("default")
        transaction.leave_transaction_management("second")

    def test_savepoints(self):
        """tests savepoints for multiple db's"""
        from Queue import Queue as queue
        q = queue()
        other = lambda x: self._run_threaded(x, q)

        from testapp.models import Genre
        try:
            from django.db import connections, transaction
        except ImportError:
            # connections doesn't exist in 1.1 and under
            print"\n  Skipping multi database tests"

        if len(getattr(settings, "DATABASES", [])) <= 1:
            print "\n  Skipping multi database tests"
            return
        for name, db in settings.DATABASES.items():
            if name in ('default', 'second'):
                if 'sqlite' in db['ENGINE']:
                    print "\n  Skipping test requiring multiple threads."
                    return
                con = connections[name]
                if not con.features.uses_savepoints:
                    print "\n  Skipping test requiring savepoints."
                    return

        # sanity check 
        self.failUnless(transaction.is_managed() == False)
        self.failUnless(transaction.is_dirty() == False)
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

        g2.title = "Committed savepoint"
        g2.save(using="second")
        sid2 = transaction.savepoint(using="second")

        sid = transaction.savepoint(using="default")
        g1.title = "Dirty text"
        g1.save()

        #other thread should see the original key and cache object from memcache,
        #not the local cache version
        other("Genre.objects.using('default').get(pk=1)")
        hit, ostart = q.get()
        self.failUnless(hit)
        self.failUnless(ostart.title == start_g1)
        #should not be a hit due to rollback
        connections["default"].queries = []
        transaction.savepoint_rollback(sid, using="default")
        g1 = Genre.objects.using("default").get(pk=1)

        # i think it should be "Rollback Savepoint" here
        self.failUnless(g1.title == start_g1)

        #will be pushed to dirty in commit
        g2 = Genre.objects.using("second").get(pk=1)
        self.failUnless(g2.title == "Committed savepoint")
        transaction.savepoint_commit(sid2, using="second")

        #other thread should still see original version even 
        #after savepoint commit
        other("Genre.objects.using('second').get(pk=1)")
        hit, ostart = q.get()
        self.failUnless(hit)
        self.failUnless(ostart.title == start_g1)

        connections["second"].queries = []
        g2 = Genre.objects.using("second").get(pk=1)
        self.failUnless(connections["second"].queries == [])

        transaction.commit(using="second")
        transaction.managed(False, "second")

        g2 = Genre.objects.using("second").get(pk=1)
        self.failUnless(connections["second"].queries == [])
        self.failUnless(g2.title == "Committed savepoint")

        #now committed and cached, other thread should reflect new title
        #without a hit to the db
        other("Genre.objects.using('second').get(pk=1)")
        hit, ostart = q.get()
        self.failUnless(ostart.title == g2.title)
        self.failUnless(hit)

        transaction.managed(False, "default")
        transaction.leave_transaction_management("default")
        transaction.leave_transaction_management("second")


class SingleModelTest(QueryCacheBase):
    fixtures = base.johnny_fixtures

    def test_multi_where_cache_coherency(self):
        """A test to detect the issue described in bitbucket #24:
        https://bitbucket.org/jmoiron/johnny-cache/issue/24/
        """
        from testapp.models import Issue24Model as i24m

        i24m.objects.get_or_create(one=1, two=1)
        i24m.objects.get_or_create(one=1, two=2)
        i24m.objects.get_or_create(one=2, two=1)
        i24m.objects.get_or_create(one=2, two=2)

        ones = i24m.objects.filter(one=1)
        twos = i24m.objects.filter(two=1)

        res = i24m.objects.filter(one__in=ones).exclude(two=twos).all()
        # XXX: I'm afraid I don't even understand what this is supposed
        # to be doing here, and in any case this test case fails.  I've
        # included something similar to the patch in #24, if someone knows
        # how to write a test case to create that condition please do so here

    def test_exists_hit(self):
        """Tests that an exist failure caches properly"""
        from testapp.models import Publisher
        connection.queries = []

        Publisher.objects.filter(title="Doesn't Exist").exists()
        Publisher.objects.filter(title="Doesn't Exist").exists()

        self.assertEqual(len(connection.queries), 1)

    def test_basic_querycaching(self):
        """A basic test that querycaching is functioning properly and is
        being invalidated properly on singular table reads & writes."""
        from testapp.models import Publisher, Genre
        from django.db.models import Q
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
        # this tests the codepath after 'except EmptyResultSet' where
        # result_type == MULTI
        self.failUnless(not list(Publisher.objects.filter(title__in=[])))
        # test for a regression on the WhereNode, bitbucket #20
        g1 = Genre.objects.get(pk=1)
        g1.title = "Survival Horror"
        g1.save()
        g1 = Genre.objects.get(Q(title__iexact="Survival Horror"))

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

    def test_delete(self):
        """Test that a database delete clears a table cache."""
        from testapp.models import Genre
        g1 = Genre.objects.get(pk=1)
        begin = Genre.objects.all().count()
        g1.delete()
        self.assertRaises(Genre.DoesNotExist, lambda: Genre.objects.get(pk=1))
        connection.queries = []
        self.failUnless(Genre.objects.all().count() == (begin -1))
        self.failUnless(len(connection.queries) == 1)
        Genre(title='Science Fiction', slug='scifi').save()
        Genre(title='Fantasy', slug='rubbish').save()
        Genre(title='Science Fact', slug='scifact').save()
        count = Genre.objects.count()
        Genre.objects.get(title='Fantasy')
        q = base.message_queue()
        Genre.objects.filter(title__startswith='Science').delete()
        # this should not be cached
        Genre.objects.get(title='Fantasy')
        self.failUnless(not q.get_nowait())

    def test_update(self):
        from testapp.models import Genre
        connection.queries = []
        g1 = Genre.objects.get(pk=1)
        Genre.objects.all().update(title="foo")
        g2 = Genre.objects.get(pk=1)
        self.failUnless(g1.title != g2.title)
        self.failUnless(g2.title == "foo")
        self.failUnless(len(connection.queries) == 3)

    def test_empty_count(self):
        """Test for an empty count aggregate query with an IN"""
        from testapp.models import Genre
        books = Genre.objects.filter(id__in=[])
        count = books.count()
        self.failUnless(count == 0)

    def test_aggregate_annotation(self):
        """Test aggregating an annotation """
        from django.db.models import Count
        from django.db.models import Sum
        from testapp.models import Book
        from django.core.paginator import Paginator
        author_count = Book.objects.annotate(author_count=Count('authors')).aggregate(Sum('author_count'))
        self.assertEquals(author_count['author_count__sum'],2)
        # also test using the paginator, although this shouldn't be a big issue..
        books = Book.objects.all().annotate(num_authors=Count('authors'))
        paginator = Paginator(books, 25)
        list_page = paginator.page(1)

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
        from johnny.signals import qc_hit, qc_miss, qc_skip
        connection.queries = []
        misses = []
        hits = []
        def qc_hit_listener(sender, **kwargs):
            hits.append(kwargs['key'])
        def qc_miss_listener(*args, **kwargs):
            misses.append(kwargs['key'])
        qc_hit.connect(qc_hit_listener)
        qc_miss.connect(qc_miss_listener)
        qc_skip.connect(qc_miss_listener)
        first = list(Genre.objects.filter(title__startswith='A').order_by('slug'))
        second = list(Genre.objects.filter(title__startswith='A').order_by('slug'))
        self.failUnless(len(misses) == len(hits) == 1)

    def test_in_values_list(self):
        from testapp.models import Publisher, Book
        from johnny.cache import get_tables_for_query
        pubs = Publisher.objects.all()
        books = Book.objects.filter(publisher__in=pubs.values_list("id", flat=True))
        tables = list(sorted(get_tables_for_query(books.query)))
        self.assertEqual(["testapp_book", "testapp_publisher"], tables)


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
        q = base.message_queue()
        b = Book.objects.get(id=1)
        invalidate(Book)
        b = Book.objects.get(id=1)
        first, second = q.get_nowait(), q.get_nowait()
        self.failUnless(first == second == False)
        g = Genre.objects.get(id=1)
        p = Publisher.objects.get(id=1)
        invalidate('testapp_genre', Publisher)
        g = Genre.objects.get(id=1)
        p = Publisher.objects.get(id=1)
        fg,fp,sg,sp = [q.get() for i in range(4)]
        self.failUnless(fg == fp == sg == sp == False)

    def test_many_to_many(self):
        from testapp.models import Book, Person
        b = Book.objects.get(pk=1)
        p1 = Person.objects.get(pk=1)
        p2 = Person.objects.get(pk=2)
        b.authors.add(p1)
        connection.queries = []

        list(b.authors.all())

        #many to many should be invalidated
        self.failUnless(len(connection.queries) == 1)
        b.authors.remove(p1)
        b = Book.objects.get(pk=1)
        list(b.authors.all())
        #can't determine the queries here, 1.1 and 1.2 uses them differently

        connection.queries = []
        #many to many should be invalidated, 
        #person is not invalidated since we just want
        #the many to many table to be
        p1 = Person.objects.get(pk=1)
        self.failUnless(len(connection.queries) == 0)

        p1.books.add(b)
        connection.queries = []

        #many to many should be invalidated,
        #this is the first query
        list(p1.books.all())
        b = Book.objects.get(pk=1)
        self.failUnless(len(connection.queries) == 1)

        #query should be cached
        self.failUnless(len(list(p1.books.all())) == 1)
        self.failUnless(len(connection.queries) == 1)

        #testing clear
        b.authors.clear()
        self.failUnless(b.authors.all().count() == 0)
        self.failUnless(p1.books.all().count() == 0)
        b.authors.add(p1)
        self.failUnless(b.authors.all().count() == 1)
        queries = len(connection.queries)

        #should be cached
        b.authors.all().count()
        self.failUnless(len(connection.queries) == queries)
        self.failUnless(p1.books.all().count() == 1)
        p1.books.clear()
        self.failUnless(b.authors.all().count() == 0)

    def test_subselect_support(self):
        """Test that subselects are handled properly."""
        from django import db
        db.reset_queries()
        from testapp.models import Book, Person, PersonType
        author_types = PersonType.objects.filter(title='Author')
        author_people = Person.objects.filter(person_types__in=author_types)
        written_books = Book.objects.filter(authors__in=author_people)
        q = base.message_queue()
        self.failUnless(len(db.connection.queries) == 0)
        count = written_books.count()
        self.failUnless(q.get() == False)
        # execute the query again, this time it's cached
        self.failUnless(written_books.count() == count)
        self.failUnless(q.get() == True)
        # change the person type of 'Author' to something else
        pt = PersonType.objects.get(title='Author')
        pt.title = 'NonAuthor'
        pt.save()
        self.failUnless(PersonType.objects.filter(title='Author').count() == 0)
        q.clear()
        db.reset_queries()
        # now execute the same query;  the result should be diff and it should be
        # a cache miss
        new_count = written_books.count()
        self.failUnless(new_count != count)
        self.failUnless(q.get() == False)
        PersonType.objects.filter(title='NonAuthor').order_by('-title')[:5]

    def test_foreign_key_delete_cascade(self):
        """From #32, test that if you have 'Foo' and 'Bar', with bar.foo => Foo,
        and you delete foo, bar.foo is also deleted, which means you have to
        invalidate Bar when deletions are made in Foo (but not changes)."""


class TransactionSupportTest(TransactionQueryCacheBase):
    fixtures = base.johnny_fixtures

    def _run_threaded(self, query, queue):
        """Runs a query (as a string) from testapp in another thread and
        puts (hit?, result) on the provided queue."""
        from threading import Thread
        def _inner(_query):
            from testapp.models import Genre, Book, Publisher, Person
            from johnny.signals import qc_hit, qc_miss, qc_skip
            msg = []
            def hit(*args, **kwargs):
                msg.append(True)
            def miss(*args, **kwargs):
                msg.append(False)
            qc_hit.connect(hit)
            qc_miss.connect(miss)
            qc_skip.connect(miss)
            obj = eval(_query)
            msg.append(obj)
            queue.put(msg)
            if connections is not None:
                #this is to fix a race condition with the
                #thread to ensure that we close it before 
                #the next test runs
                connections['default'].close()
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

        if django.VERSION[:2] < (1, 3):
            if settings.DATABASE_ENGINE == 'sqlite3':
                print "\n  Skipping test requiring multiple threads."
                return
        else:
            if settings.DATABASES.get('default', {}).get('ENGINE', '').endswith('sqlite3'):
                print "\n  Skipping test requiring multiple threads."
                return


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
        if django.VERSION[:2] < (1, 3):
            if settings.DATABASE_ENGINE == 'sqlite3':
                print "\n  Skipping test requiring multiple threads."
                return
        else:
            if settings.DATABASES.get('default', {}).get('ENGINE', '').endswith('sqlite3'):
                print "\n  Skipping test requiring multiple threads."
                return

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

import johnny
class TransactionManagerTestCase(base.TransactionJohnnyTestCase):

    def setUp(self):
        self.middleware = middleware.QueryCacheMiddleware()
    
    def tearDown(self):
        from django.db import transaction
        if transaction.is_managed():
            transaction.managed(False)

    def test_savepoint_localstore_flush(self):
        """
        This is a very simple test to see if savepoints will actually
        be committed, i.e. flushed out from localstore into cache.
        """
        from django.db import transaction
        transaction.enter_transaction_management()
        transaction.managed()

        TABLE_NAME = 'test_table'
        cache_backend = johnny.cache.get_backend()
        cache_backend.patch()
        keyhandler = cache_backend.keyhandler
        keygen = keyhandler.keygen
        
        tm = cache_backend.cache_backend
        
        # First, we set one key-val pair generated for our non-existing table.
        table_key = keygen.gen_table_key(TABLE_NAME)
        tm.set(table_key, 'val1')

        # Then we create a savepoint.
        # The key-value pair is moved into 'trans_sids' item of localstore.
        tm._create_savepoint('savepoint1')
        
        # We then commit all the savepoints (i.e. only one in this case)
        # The items stored in 'trans_sids' should be moved back to the
        # top-level dictionary of our localstore
        tm._commit_all_savepoints()
        # And this checks if it actually happened.
        self.failUnless(table_key in tm.local)

class ParamsClashBug(QueryCacheBase):
    fixtures = base.johnny_fixtures
    def test_params(self):

        from testapp.models import PersonType, Person
        for i in range(2, 22):
            pt, _ = PersonType.objects.get_or_create(title='title %s' % i, slug='slug_%s' % i)
            p = Person()
            p.first_name = 'first name'
            p.last_name = 'last name'
            p.slug = 'person_%s' % i
            p.gender = 1
            p.save()
            p.person_types.add(pt)

        person_A = Person.objects.get(id = 1)
        person_B = Person.objects.get(id = 12)
        person_A.person_types.add(PersonType.objects.get(id = 21))
        person_B.person_types.add(PersonType.objects.get(id = 1))

        qset = person_A.person_types.through._default_manager.values_list('persontype', flat=True)
        qset_A = qset.filter(person = 1, persontype__in = [21])
        qset_B = qset.filter(person = 12, persontype__in = [1])

        self.assertTrue(list(qset_A) == [21])
        self.assertTrue(list(qset_B) == [1])
