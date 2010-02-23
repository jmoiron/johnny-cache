#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Johnny provides one backend, is a version of the django cache backend that
allows a timeout of ``0`` to fall through to the "real" cache backend.  For
``memcached``, this means "cache forever."

This is essentially the same as mmalone's inspiring ``django-caching``
application's `cache backend monkey-patch
<http://github.com/mmalone/django-caching/blob/master/app/cache.py>`_.
"""

from django.core.cache import cache
from django.utils.encoding import smart_str

class InfinityCache(cache.__class__):
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

