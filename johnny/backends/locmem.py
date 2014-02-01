"""
Infinite caching locmem class.  Caches forever when passed timeout of 0.

This actually doesn't cache "forever", just for a very long time.  On
32 bit systems, it will cache for 68 years, quite a bit longer than any
computer will last.  On a 64 bit machine, your cache will expire about
285 billion years after the Sun goes red-giant and destroys Earth.
"""

import sys
from django.core.cache.backends import locmem


class LocMemCache(locmem.LocMemCache):

    def add(self, key, value, timeout=None, **kwargs):
        if timeout is 0:
            timeout = sys.maxsize
        return super(LocMemCache, self).add(
            key, value, timeout=timeout, **kwargs)

    def set(self, key, value, timeout=None, **kwargs):
        if timeout is 0:
            timeout = sys.maxsize
        return super(LocMemCache, self).set(
            key, value, timeout=timeout, **kwargs)
