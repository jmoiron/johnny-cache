#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for the QueryCache functionality of johnny."""

from django.conf import settings
from django.db import connection
from johnny import middleware
import base

try:
    any
except NameError:
    def any(iterable):
        for i in iterable:
            if i: return True
        return False

# put tests in here to be included in the testing suite
__all__ = ['TestFullRequestStack']

class TestFullRequestStack(base.TransactionJohnnyWebTestCase):
    fixtures = base.johnny_fixtures

    def test_queries_from_templates(self):
        connection.queries = []
        response = self.client.get('/test/template_queries')
        self.failUnless(len(connection.queries) == 1)
        response = self.client.get('/test/template_queries')
        self.failUnless(len(connection.queries) == 1)

