#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django.db import transaction as django_transaction
from django.db import connection
try:
    from django.db import DEFAULT_DB_ALIAS
except:
    DEFUALT_DB_ALIAS = None

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
        self._dirty_backup = {}

        self._sids = []

    def is_managed(self):
        return django_transaction.is_managed()

    def get(self, key, default=None):
        if self.is_managed() and self._patched_var:
            val = self.local.get(key, None)
            if val: return val
            if self._uses_savepoints():
                val = self._get_from_savepoints(key)
                if val: return val

        return self.cache_backend.get(key, default)

    def _get_from_savepoints(self, key):
        cp = list(self._sids)
        cp.reverse()
        for sid in cp:
            if key in self.local[sid]:
                return self.local[sid][key]

    def set(self, key, val):
        """
        Set will be using the generational key, so if another thread
        bumps this key, the localstore version will still be invalid.
        If the key is bumped during a transaction it will be new
        to the global cache on commit, so it will still be a bump.
        """
        if self.is_managed() and self._patched_var:
            self.local[key] = val
        else:
            self.cache_backend.set(key, val)

    def _clear(self):
        self.local.clear('jc_*')

    def _flush(self, commit=True, using=None):
        """
        Flushes the internal cache, either to the memcache or rolls back
        """
        if commit:
            # XXX: multi-set? 
            if self._uses_savepoints():
                self._commit_all_savepoints()
            c = self.local.mget('jc_*')
            for key, value in c.iteritems():
                self.cache_backend.set(key, value)
        else:
            if self._uses_savepoints():
                self._rollback_all_savepoints()
        self._clear()

    def _patched(self, original, commit=True):
        @wraps(original)
        def newfun(using=None):
            #1.2 version
            original(using=using)
            self._flush(commit=commit, using=using)

        @wraps(original)
        def newfun11():
            #1.1 version
            original()
            self._flush(commit=commit)
        if django.VERSION[:2] == (1,1): return newfun11
        if django.VERSION[:2] == (1,2): return newfun

    def _uses_savepoints(self):
        return connection.features.uses_savepoints

    def _sid_key(self, sid):
        return 'trans_savepoint_%s'%sid

    def _create_savepoint(self, sid):
        key = self._sid_key(sid)

        #get all local dirty items
        c = self.local.mget('jc_*')
        #store them to a dictionary in the localstore
        if key not in self.local:
            self.local[key] = {}
        for k, v in c.iteritems():
            self.local[key][k] = v
        #clear the dirty
        self._clear()
        #append the key to the savepoint stack
        self._sids.append(key)

    def _rollback_savepoint(self, sid, using=None):
        key = self._sid_key(sid)
        stack = []
        try:
            popped = None
            while popped != key:
                popped = self._sids.pop()
                stack.insert(0, popped)
            #delete items from localstore
            for i in stack:
                del self.local[i]
            #clear dirty
            self._clear()
        except IndexError, e:
            #key not found, don't delete from localstore, restore sid stack
            for i in stack:
                self._sids.insert(0, i)

    def _commit_savepoint(self, sid):
        #commit is not a commit but is in reality just a clear back to that savepoint
        #and adds the items back to the dirty transaction.
        key = self._sid_key(sid)
        stack = []
        try:
            popped = None
            while popped != key:
                popped = self._sids.pop()
                stack.insert(0, popped)
            self._store_dirty()
            for i in stack:
                for k, v in self.local[i].iteritems():
                    self._local[k] = v
                del self.local[i]
            self._restore_dirty()
        except IndexError, e:
            for i in stack:
                self._sids.insert(0, i)

    def _commit_all_savepoints(self):
        if self._sids:
            self._commit_savepoint(self._sids[0])

    def _rollback_all_savepoints(self):
        if self._sids:
            self._rollback_savepoint(self._sids[0])

    def _store_dirty(self):
        c = self.local.mget('jc_*')
        backup = 'trans_dirty_store'
        if backup not in self.local:
            self.local[backup] = {}
        for k, v in c.iteritems():
            self.local[backup][k] = v
        self._clear()

    def _restore_dirty(self):
        backup = 'trans_dirty_store'
        for k, v in self.local.get(backup, {}).iteritems():
            self.local[k] = v
        del self.local[backup]

    def _savepoint(self, original):
        @wraps(original)
        def newfun(using=None):
            if using != None:
                sid = original(using=using)
            else:
                sid = original()
            if self._uses_savepoints():
                self._create_savepoint(sid)
            return sid
        return newfun

    def _savepoint_rollback(self, original):
        def newfun(sid, *args, **kwargs):
            original(sid, *args, **kwargs)
            if self._uses_savepoints():
                self._rollback_savepoint(sid)
        return newfun

    def _savepoint_commit(self, original):
        def newfun(sid, *args, **kwargs):
            original(sid, *args, **kwargs)
            if self._uses_savepoints():
                self._commit_savepoint(sid)
        return newfun
            
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
            django_transaction.commit = self._patched(django_transaction.commit, True)

            self._originals['savepoint'] = django_transaction.savepoint
            django_transaction.savepoint = self._savepoint(django_transaction.savepoint)
            self._originals['savepoint_rollback'] = django_transaction.savepoint_rollback
            django_transaction.savepoint_rollback = self._savepoint_rollback(django_transaction.savepoint_rollback)
            self._originals['savepoint_commit'] = django_transaction.savepoint_commit
            django_transaction.savepoint_commit = self._savepoint_commit(django_transaction.savepoint_commit)

            self._patched_var = True

    def unpatch(self):
        for fun in self._originals:
            setattr(django_transaction, fun, self._originals[fun])

        self._patched_var = False


