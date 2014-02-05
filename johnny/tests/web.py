#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for the QueryCache functionality of johnny."""

from . import base


# put tests in here to be included in the testing suite
__all__ = ['MiddlewaresTestCase']


class MiddlewaresTestCase(base.TransactionJohnnyWebTestCase):
    fixtures = base.johnny_fixtures
    middlewares = (
        'johnny.middleware.LocalStoreClearMiddleware',
        'johnny.middleware.QueryCacheMiddleware',
        'django.middleware.common.CommonMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
        'django.middleware.locale.LocaleMiddleware',
        'django.middleware.gzip.GZipMiddleware',
        'django.middleware.http.ConditionalGetMiddleware',
    )

    def test_queries_from_templates(self):
        """Verify that doing the same request w/o a db write twice does not
        populate the cache properly."""
        with self.assertNumQueries(1):
            self.client.get('/test/template_queries')
        with self.assertNumQueries(0):
            self.client.get('/test/template_queries')
