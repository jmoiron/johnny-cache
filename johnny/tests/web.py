#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for the QueryCache functionality of johnny."""

from django.conf import settings
from django.db import connection
from johnny import middleware
import django
import base

try:
    any
except NameError:
    def any(iterable):
        for i in iterable:
            if i: return True
        return False

# put tests in here to be included in the testing suite
__all__ = ['TestTransactionMiddleware', 'TestJohnnyTransactionMiddleware']

class TestTransactionMiddleware(base.TransactionJohnnyWebTestCase):
    """This test checks for errant behavior in Django's default transaction
    middleware.  This middleware doesn't commit clean transactions, which
    means that clean transactions never make it to the cache."""
    fixtures = base.johnny_fixtures
    middleware = (
        'johnny.middleware.LocalStoreClearMiddleware',
        'johnny.middleware.QueryCacheMiddleware',
        'django.middleware.common.CommonMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        #'django.contrib.messages.middleware.MessageMiddleware',
        'django.middleware.locale.LocaleMiddleware',
        'django.middleware.gzip.GZipMiddleware',
        'django.middleware.http.ConditionalGetMiddleware',
        'django.middleware.transaction.TransactionMiddleware',
    )

    def test_queries_from_templates(self):
        """Verify that doing the same request w/o a db write twice does not
        populate the cache properly."""
        # it seems that django 1.3 doesn't exhibit this bug!
        if django.VERSION[:2] >= (1, 3):
            return
        connection.queries = []
        q = base.message_queue()
        response = self.client.get('/test/template_queries')
        self.failUnless(q.get() is False)
        response = self.client.get('/test/template_queries')
        self.failUnless(q.get() is False)

class TestJohnnyTransactionMiddleware(base.TransactionJohnnyWebTestCase):
    """This test verifies that a workaround middleware provided with johnny
    does not exhibit the same errant behavior as the builtin middleware."""
    fixtures = base.johnny_fixtures
    middleware = (
        'johnny.middleware.LocalStoreClearMiddleware',
        'johnny.middleware.QueryCacheMiddleware',
        'django.middleware.common.CommonMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        #'django.contrib.messages.middleware.MessageMiddleware',
        'django.middleware.locale.LocaleMiddleware',
        'django.middleware.gzip.GZipMiddleware',
        'django.middleware.http.ConditionalGetMiddleware',
        'johnny.middleware.CommittingTransactionMiddleware',
    )

    def test_queries_from_templates(self):
        """Verify that doing the same request w/o a db write twice *does*
        populate the cache properly."""
        connection.queries = []
        q = base.message_queue()
        response = self.client.get('/test/template_queries')
        self.failUnless(q.get() is False)
        response = self.client.get('/test/template_queries')
        self.failUnless(q.get() is True)

