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
        from django.core.management import call_command
        from testapp.models import Publisher
        connection.queries = []
        starting_count = Publisher.objects.count()
        starting_count = Publisher.objects.count()
        # make sure that doing this twice doesn't hit the db twice
        self.failUnless(len(connection.queries) == 1)
        self.failUnless(len(starting_count) == 1)

