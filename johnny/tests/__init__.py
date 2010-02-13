#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for johnny cache.  This test module uses roughly the layout suggested
by julien in a ticket about test-only models:

http://code.djangoproject.com/ticket/7835#comment:21

"""

import sys

from django.test import TestCase
from django.conf import settings
from django.core.management import call_command
from django.db.models.loading import load_app

# import the other tests from johnny
from localstore import LocalStoreTest

from testapp.models import *


