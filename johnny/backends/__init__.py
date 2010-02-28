#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Johnny provides two backends, both of which are subclassed versions of
django builtins that cache "forever" when passed a 0 timeout.

This is essentially the same as mmalone's inspiring ``django-caching``
application's `cache backend monkey-patch
<http://github.com/mmalone/django-caching/blob/master/app/cache.py>`_.

To use these backends, change your ``CACHE_BACKEND`` setting to something
like::

    CACHE_BACKEND="johnny.backends.memcached://.."
"""

__all__ = ['memcached', 'locmem']

