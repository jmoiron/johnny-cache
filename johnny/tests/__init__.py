#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for johnny cache.  This test module uses roughly the layout suggested
by julien in a ticket about test-only models:

http://code.djangoproject.com/ticket/7835#comment:21

"""

# the 'base' test class for johnny is locaded in base.py

# import the other tests from johnny
from localstore import LocalStoreTest
from cache import *
from web import *

from testapp.models import *

