#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Middleware classes for johnny cache."""

def apply_patch():
    pass

class GenerationalCacheMiddleware(object):
    """This middleware class monkey-patches django's ORM to maintain
    generational info on each table (model) in the cache.  This allows other
    applications to cache using these keys, and have their caching
    automatically drop out when the tables are updated in some way.  This
    should be the first middleware in your middleware stack."""
    __state = {} # alex martinelli's borg pattern
    def __init__(self):
        self.__dict__ = self.__state
        from django.conf import settings
        self.disabled = getattr(settings, 'DISABLE_GENERATIONAL_CACHE', False)
        self.installed = getattr(self, 'installed', False)
        if not self.installed:
            apply_patch()
            self.installed = True
