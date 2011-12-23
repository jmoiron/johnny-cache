"""
Infinite file-based caching.  Caches forever when passed timeout of 0.
"""

import sys

import django
from django.core.cache.backends import filebased

# NOTE: We aren't using smart_str here, because the underlying library will
# perform a call to md5 that chokes on that type of input;  we'll just not
# fret the encoding, and things will work alright even with unicode table
# names


class CacheClass(filebased.CacheClass):
    def add(self, key, value, timeout=None, **kwargs):
        if timeout is 0:
            timeout = sys.maxint
        return super(CacheClass, self).add(
            key, value, timeout=timeout, **kwargs)

    def set(self, key, value, timeout=None, **kwargs):
        if timeout is 0:
            timeout = sys.maxint
        return super(CacheClass, self).set(
            key, value, timeout=timeout, **kwargs)

if django.VERSION[:2] > (1, 2):

    class FileBasedCache(CacheClass):
        """
        File based cache named according to Django >= 1.3 conventions.
        """
        pass
