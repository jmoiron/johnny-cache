#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Middleware classes for johnny cache."""

from django.core.exceptions import ImproperlyConfigured
import django
import cache

class QueryCacheMiddleware(object):
    """This middleware class monkey-patches django's ORM to maintain
    generational info on each table (model) and to automatically cache all
    querysets created via the ORM.  This should be the first middleware
    in your middleware stack."""
    __state = {} # alex martinelli's borg pattern
    def __init__(self):
        self.__dict__ = self.__state
        from django.conf import settings
        self.disabled = getattr(settings, 'DISABLE_GENERATIONAL_CACHE', False)
        self.installed = getattr(self, 'installed', False)
        if not self.installed and not disabled:
            self.query_cache_backend = self._get_backend()
            self.query_cache_backend.patch()
            self.installed = True

    def unpatch(self):
        self.query_cache_backend.unpatch()

    def _get_backend(self):
        if django.VERSION[:2] == (1, 1):
            return cache.QueryCacheBackend11()
        if django.VERSION[:2] == (1, 2):
            return cache.QueryCacheBackend()
        raise ImproperlyConfigured("QueryCacheMiddleware cannot patch your version of django.")

