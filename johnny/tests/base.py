#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Base test class for Johnny Cache Tests."""

import sys

from django.test import TestCase, TransactionTestCase
from django.conf import settings
from django.core.management import call_command
from django.db.models.loading import load_app

from johnny import settings as johnny_settings

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

class TransactionJohnnyWebTestCase(TransactionJohnnyTestCase):
    def _pre_setup(self):
        from johnny import middleware
        self.saved_MIDDLEWARE_CLASSES = settings.MIDDLEWARE_CLASSES
        if getattr(self.__class__, 'middleware', None):
            settings.MIDDLEWARE_CLASSES = self.__class__.middleware
        self.saved_DISABLE_SETTING = getattr(johnny_settings, 'DISABLE_QUERYSET_CACHE', False)
        johnny_settings.DISABLE_QUERYSET_CACHE = False
        self.middleware = middleware.QueryCacheMiddleware()
        self.saved_ROOT_URLCONF = settings.ROOT_URLCONF
        settings.ROOT_URLCONF = 'johnny.tests.testapp.urls'
        super(TransactionJohnnyWebTestCase, self)._pre_setup()

    def _post_teardown(self):
        self.middleware.unpatch()
        johnny_settings.DISABLE_QUERYSET_CACHE = self.saved_DISABLE_SETTING
        settings.MIDDLEWARE_CLASSES = self.saved_MIDDLEWARE_CLASSES
        settings.ROOT_URLCONF = self.saved_ROOT_URLCONF
        super(TransactionJohnnyWebTestCase, self)._post_teardown()

class message_queue(object):
    """Return a message queue that gets 'hit' or 'miss' messages.  The signal
    handlers use weakrefs, so if we don't save references to this object they
    will get gc'd pretty fast."""
    def __init__(self):
        from johnny.signals import qc_hit, qc_miss
        from Queue import Queue as queue
        self.q = queue()
        qc_hit.connect(self._hit)
        qc_miss.connect(self._miss)

    def _hit(self, *a, **k): self.q.put(True)
    def _miss(self, *a, **k): self.q.put(False)

    def clear(self):
        while not self.q.empty():
            self.q.get_nowait()
    def get(self): return self.q.get()
    def get_nowait(self): return self.q.get_nowait()
    def qsize(self): return self.q.qsize()
    def empty(self): return self.q.empty()

