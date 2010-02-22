#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django.db import transaction as django_transaction

try:
    from functools import wraps
except ImportError:
    from django.utils.functional import wraps  # Python 2.3, 2.4 fallback.

import django

class TransactionManager(object):
    """
    TransactionManager is a wrapper around a cache_backend that is transaction aware in django.
    Basically, if we are in a transaction it will return the locally cached version. 
    On rollback, it will flush all local caches
    On commit, it will push them up to the cache backend
    """
    _patched_var = False
    def __init__(self, cache_backend):
        from johnny import cache
        self.cache_backend = cache_backend
        self.local = cache.local
        self._originals = {}

    def is_dirty(self):
        return django_transaction.is_dirty()

    def get(self, key, default=None):
        if self.is_dirty() and self._patched_var:
            val = self.local.get(key, None)
            if val: return val
        return self.cache_backend.get(key, default)

    def set(self, key, val):
        """
        Set will be using the generational key, so if another thread
        bumps this key, the localstore version will still be invalid.
        If the key is bumped during a transaction it will be new
        to the global cache on commit, so it will still be a bump.
        """
        if self.is_dirty() and self._patched_var:
            self.local[key] = val
        else:
            self.cache_backend.set(key, val)

    def _clear(self):
        self.local.clear('jc_*')

    def _flush(self, commit=True):
        """
        Flushes the internal cache, either to the memcache or rolls back
        """
        if commit:
            # XXX: multi-set? 
            c = self.local.mget('jc_*')
            for key, value in c.iteritems():
                self.cache_backend.set(key, value)
        self._clear()

    def _patched(self, original, commit=True):
        @wraps(original)
        def newfun(using=None):
            #1.2 version
            original(using=using)
            self._flush(commit=commit)

        @wraps(original)
        def newfun11():
            #1.1 version
            original()
            self._flush(commit=commit)
        if django.VERSION[:2] == (1,1): return newfun11
        if django.VERSION[:2] == (1,2): return newfun

    def patch(self):
        """
        This function monkey patches commit and rollback
        writes to the cache should not happen until commit (unless our state isn't managed).
        It does not yet support savepoints.
        """
        if not self._patched_var:
            self._originals['rollback'] = django_transaction.rollback
            self._originals['commit'] = django_transaction.commit
            django_transaction.rollback = self._patched(django_transaction.rollback, False)
            django_transaction.commit = self._patched(django_transaction.rollback, True)
            self._patched_var = True

    def unpatch(self):
        django_transaction.rollback = self._originals['rollback']
        django_transaction.commit = self._originals['commit']
        self._patched_var = False


