#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for the QueryCache functionality of johnny."""

from django.conf import settings
from django.db import connection
from johnny import middleware
import base

# put tests in here to be included in the testing suite
__all__ = ['SingleModelTest',]

class QueryCacheBase(base.JohnnyTestCase):
    def _pre_setup(self):
        self.saved_DISABLE_SETTING = getattr(settings, 'DISABLE_GENERATIONAL_CACHE', False)
        self.DISABLE_GENERATIONAL_CACHE = False
        self.middleware = middleware.QueryCacheMiddleware()
        super(QueryCacheBase, self)._pre_setup()

    def _post_teardown(self):
        self.middleware.unpatch()
        self.DISABLE_GENERATIONAL_CACHE = self.saved_DISABLE_SETTING
        super(QueryCacheBase, self)._post_teardown()


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
        first = list(Genre.objects.order_by('slug'))
        second = list(Genre.objects.order_by('-slug'))
        # test that we've indeed done two queries and that the orders
        # of the results are reversed
        self.failUnless((first[0], first[1] == second[1], second[0]))
        self.failUnless(len(connection.queries) == 2)


