#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Infinite caching locmem class.  Caches forever when passed timeout of 0.

This actually doesn't cache "forever", just for a very long time.  On
32 bit systems, it will cache for 68 years, quite a bit longer than any
computer will last.  On a 64 bit machine, your cache will expire about
285 billion years after the Sun goes red-giant and destroys Earth.

To use, change your ``CACHE_BACKEND`` setting to something like this::

    CACHE_BACKEND="johnny.backends.locmem://.."
"""

from django.core.cache.backends import locmem
from django.utils.encoding import smart_str
import sys

class CacheClass(locmem.CacheClass):
    def add(self, key, value, timeout=None):
        timeout = sys.maxint if timeout is 0 else timeout
        return super(CacheClass, self).add(smart_str(key), value, timeout)

    def set(self, key, value, timeout=None):
        timeout = sys.maxint if timeout is 0 else timeout
        return super(CacheClass, self).set(smart_str(key), value, timeout)


