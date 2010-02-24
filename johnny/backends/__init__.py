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

__all__ = ['memcached', 'locmem']

