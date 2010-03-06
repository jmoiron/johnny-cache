#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Middleware classes for johnny cache."""

import django
from django.core.exceptions import ImproperlyConfigured
from django.core.cache import cache as django_cache
from johnny import cache

class QueryCacheMiddleware(object):
    """This middleware class monkey-patches django's ORM to maintain
    generational info on each table (model) and to automatically cache all
    querysets created via the ORM.  This should be the first middleware
    in your middleware stack."""
    __state = {} # alex martinelli's borg pattern
    def __init__(self):
        self.__dict__ = self.__state
        from django.conf import settings
        self.disabled = getattr(settings, 'DISABLE_QUERYSET_CACHE', False)
        self.installed = getattr(self, 'installed', False)
        if not self.installed and not self.disabled:
            # when we install, lets refresh the blacklist, just in case johnny
            # was loaded before the setting exists somehow...
            blacklist = getattr(settings, 'MAN_IN_BLACKLIST',
                        getattr(settings, 'JOHNNY_TABLE_BLACKLIST', []))
            cache.blacklist = set(blacklist)
            self.query_cache_backend = cache.get_backend()(django_cache)
            self.query_cache_backend.patch()
            self.installed = True

    def unpatch(self):
        self.query_cache_backend.unpatch()
        self.query_cache_backend.flush_query_cache()
        self.installed = False

class LocalStoreClearMiddleware(object):
    """This middleware clears the localstore cache in `johnny.cache.local`
    at the end of every request."""
    def process_exception(self, *args, **kwargs):
        cache.local.clear()
        raise

    def process_response(self, req, resp):
        cache.local.clear()
        return resp

