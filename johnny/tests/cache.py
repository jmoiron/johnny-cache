#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for the QueryCache functionality of johnny."""

from django.conf import settings
from django.db import connection
from johnny import middleware
import base

# put tests in here to be included in the testing suite
__all__ = ['SimpleJohnnyTest',]

class QueryCacheBase(base.JohnnyTestCase):
    def setUp(self):
        self.saved_DISABLE_SETTING = getattr(settings, 'DISABLE_GENERATIONAL_CACHE', False)
        self.DISABLE_GENERATIONAL_CACHE = False
        self.middleware = middleware.QueryCacheMiddleware()
        super(QueryCacheBase, self).setUp()

    def tearDown(self):
        self.middleware.unpatch()
        self.DISABLE_GENERATIONAL_CACHE = self.saved_DISABLE_SETTING
        super(QueryCacheBase, self).tearDown()


class SimpleJohnnyTest(QueryCacheBase):
    fixtures = base.johnny_fixtures

    def test_basic_nonsense(self):
        pass

class SingleItemGetTest(QueryCacheBase):
    fixtures = base.johnny_fixtures

    def test_basic_querycaching(self):
        print "Hello!"

