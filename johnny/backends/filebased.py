"""
Infinite file-based caching.  Caches forever when passed timeout of 0.
"""

import sys

from django.core.cache.backends import filebased

# NOTE: We aren't using smart_str here, because the underlying library will
# perform a call to md5 that chokes on that type of input;  we'll just not
# fret the encoding, and things will work alright even with unicode table
# names


class FileBasedCache(filebased.FileBasedCache):
    def add(self, key, value, timeout=None, **kwargs):
        if timeout is 0:
            timeout = sys.maxsize
        return super(FileBasedCache, self).add(
            key, value, timeout=timeout, **kwargs)

    def set(self, key, value, timeout=None, **kwargs):
        if timeout is 0:
            timeout = sys.maxsize
        return super(FileBasedCache, self).set(
            key, value, timeout=timeout, **kwargs)
