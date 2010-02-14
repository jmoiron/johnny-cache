#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Base test class for Johnny Cache Tests."""

import sys

from django.test import TestCase
from django.conf import settings
from django.core.management import call_command
from django.db.models.loading import load_app

johnny_fixtures = ['authors.json', 'books.json', 'genres.json', 'publishers.json']

class JohnnyTestCase(TestCase):
    def setUp(self):
        self.saved_INSTALLED_APPS = settings.INSTALLED_APPS
        test_app = 'johnny.tests.testapp'
        settings.INSTALLED_APPS = tuple(
            list(self.saved_INSTALLED_APPS) + [test_app]
        )
        # load our fake application and syncdb
        load_app(test_app)
        print 'syncdb'
        call_command('syncdb', verbosity=0, interactive=False)
        super(JohnnyTestCase, self).setUp()

    def tearDown(self):
        settings.INSTALLED_APPS = self.saved_INSTALLED_APPS
        super(JohnnyTestCase, self).tearDown()

