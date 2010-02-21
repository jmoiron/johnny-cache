from django.db import transaction as django_transaction
try:
    import thread
except ImportError:
    import dummy_thread as thread
try:
    from functools import wraps
except ImportError:
    from django.utils.functional import wraps  # Python 2.3, 2.4 fallback.
import localstore

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
        self.cache_backend = cache_backend

        if 'jc_tm_transaction_store' not in localstore.Cache:
            localstore.Cache['jc_tm_transaction_store'] = {}
        self.local_cache = localstore.Cache['jc_tm_transaction_store']
        self.patch()

    def is_dirty(self):
        return django_transaction.is_dirty()

    def get(self, key, default=None):
        if self.is_dirty():
            val = self.local_cache.get(key, None)
            if val: return val
        return self.cache_backend.get(key, default)

    def set(self, key, val):
        """
        Set will be using the generational key, so if another thread
        bumps this key, the localstore version will still be invalid.
        If the key is bumped during a transaction it will be new
        to the global cache on commit, so it will still be a bump.
        """
        if self.is_dirty():
            self.local_cache[key] = val
        else:
            self.cache_backend.set(key, val)

    def _clear(self):
        self.local_cache = {}
        localstore.Cache['jc_tm_transaction_store'] = self.local_cache

    def _flush(self, commit=True):
        """
        Flushes the internal cache, either to the memcache or rolls back
        """
        if commit:
            for key, value in self.local_cache.iteritems():
                self.cache_backend[key] = value
        self._clear()

    def _get_using(*args, **kwargs):
        if 'using' in kwargs:
            return kwargs['using']
        if args:
            return args[-1]
        return None

    def _patched(self, original, commit=True):
        @wraps(original)
        def newfun(*args, **kwargs):
            #parsing using here since change 1.1 does not use it
            using = self._get_using(*args, **kwargs)
            if using:
                original(using=using)
            else:
                original()
            self._flush(commit=commit)
        return newfun
    
    def patch(self):
        """
        This function monkey patches commit and rollback
        writes to the cache should not happen until commit (unless our state isn't managed).
        It does not yet support savepoints.
        """
        if not self._patched_var:
            django_transaction.rollback = self._patched(django_transaction.rollback, False)
            django_transaction.commit = self._patched(django_transaction.rollback, True)
            self._patched_var = True

