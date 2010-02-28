#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Infinite caching memcached class.  Caches forever when passed a timeout
of 0. To use, change your ``CACHE_BACKEND`` setting to something like this::

    CACHE_BACKEND="johnny.backends.memcached://.."
"""

from django.core.cache.backends import memcached
from django.utils.encoding import smart_str

class CacheClass(memcached.CacheClass):
    """By checking ``timeout is None`` rather than ``not timeout``, this
    cache class allows for non-expiring cache writes on certain backends,
    notably memcached."""
    def add(self, key, value, timeout=None):
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        if timeout is None:
            timeout = self.default_timeout
        return self._cache.add(smart_str(key), value, timeout)

    def set(self, key, value, timeout=None):
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        if timeout is None:
            timeout = self.default_timeout
        self._cache.set(smart_str(key), value, timeout)


