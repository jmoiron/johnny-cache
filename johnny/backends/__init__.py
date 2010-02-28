#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Johnny provides two backends, both of which are subclassed versions of
django builtins that cache "forever" when passed a 0 timeout. These
are essentially the same as mmalone's inspiring ``django-caching``
application's `cache backend monkey-patch
<http://github.com/mmalone/django-caching/blob/master/app/cache.py>`_.
"""

__all__ = ['memcached', 'locmem']

