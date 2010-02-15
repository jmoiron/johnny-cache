#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Base test class for Johnny Cache Tests."""

import sys

from django.test import TestCase
from django.conf import settings
from django.core.management import call_command
from django.db.models.loading import load_app

# order matters here;  I guess we aren't deferring foreign key checking :\
johnny_fixtures = ['authors.json', 'genres.json', 'publishers.json', 'books.json']

class JohnnyTestCase(TestCase):
    def __init__(self, *args, **kwargs):
        super(JohnnyTestCase, self).__init__(*args, **kwargs)

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
        self.fixtures = getattr(self, 'fixtures', [])
        super(JohnnyTestCase, self)._pre_setup()

    def _post_teardown(self):
        settings.INSTALLED_APPS = self.saved_INSTALLED_APPS
        settings.DEBUG = self.saved_DEBUG
        super(JohnnyTestCase, self)._post_teardown()

