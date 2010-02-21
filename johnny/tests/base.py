#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Base test class for Johnny Cache Tests."""

import sys

from django.test import TestCase, TransactionTestCase
from django.conf import settings
from django.core.management import call_command
from django.db.models.loading import load_app

# order matters here;  I guess we aren't deferring foreign key checking :\
johnny_fixtures = ['authors.json', 'genres.json', 'publishers.json', 'books.json']

def _pre_setup(self):
    self.saved_INSTALLED_APPS = settings.INSTALLED_APPS
    self.saved_DEBUG = settings.DEBUG
    test_app = 'johnny.tests.testapp'
    settings.INSTALLED_APPS = tuple(
        list(self.saved_INSTALLED_APPS) + [test_app]
    )
    settings.DEBUG = True
    # load our fake application and syncdb
    load_app(test_app)
    call_command('syncdb', verbosity=0, interactive=False)

def _post_teardown(self):
    settings.INSTALLED_APPS = self.saved_INSTALLED_APPS
    settings.DEBUG = self.saved_DEBUG


class JohnnyTestCase(TestCase):
    def _pre_setup(self):
        _pre_setup(self)
        super(JohnnyTestCase, self)._pre_setup()

    def _post_teardown(self):
        _post_teardown(self)
        super(JohnnyTestCase, self)._post_teardown()

class TransactionJohnnyTestCase(TransactionTestCase):
    def _pre_setup(self):
        _pre_setup(self)
        super(TransactionJohnnyTestCase, self)._pre_setup()

    def _post_teardown(self):
        _post_teardown(self)
        super(TransactionJohnnyTestCase, self)._post_teardown()

