#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Backend's for Johnny."""

# This is essentially from mmalone's inspiring `django-caching` application,
#   http://github.com/mmalone/django-caching/blob/master/app/cache.py

from django.core.cache import cache
from django.utils.encoding import smart_str

# by checking is None rather than 'not timeout', you allow 0 to drop through
# which memcached backend interprets as 'forever'

class InfintyCache(cache.__class__):
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

