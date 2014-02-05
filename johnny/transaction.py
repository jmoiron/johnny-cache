from django.db import transaction, connection, DEFAULT_DB_ALIAS

from johnny import settings as johnny_settings
from johnny.compat import is_managed
from johnny.decorators import wraps, available_attrs


class TransactionManager(object):
    """
    TransactionManager is a wrapper around a cache_backend that is
    transaction aware.

    If we are in a transaction, it will return the locally cached version.

      * On rollback, it will flush all local caches
      * On commit, it will push them up to the real shared cache backend
        (ex. memcached).
    """
    _patched_var = False

    def __init__(self, cache_backend, keygen):
        from johnny import cache, settings

        self.timeout = settings.MIDDLEWARE_SECONDS
        self.prefix = settings.MIDDLEWARE_KEY_PREFIX

        self.cache_backend = cache_backend
        self.local = cache.local
        self.keygen = keygen(self.prefix)
        self._originals = {}
        self._dirty_backup = {}

        self.local['trans_sids'] = {}

    def _get_sid(self, using=None):
        if 'trans_sids' not in self.local:
            self.local['trans_sids'] = {}
        d = self.local['trans_sids']
        if using is None:
            using = DEFAULT_DB_ALIAS
        if using not in d:
            d[using] = []
        return d[using]

    def _clear_sid_stack(self, using=None):
        if using is None:
            using = DEFAULT_DB_ALIAS
        if using in self.local.get('trans_sids', {}):
            del self.local['trans_sids']

    def is_managed(self, using=None):
        return is_managed(using=using)

    def get(self, key, default=None, using=None):
        if self.is_managed(using) and self._patched_var:
            val = self.local.get(key, None)
            if val:
                return val
            if self._uses_savepoints():
                val = self._get_from_savepoints(key, using)
                if val:
                    return val
        return self.cache_backend.get(key, default)

    def _get_from_savepoints(self, key, using=None):
        sids = self._get_sid(using)
        cp = list(sids)
        cp.reverse()
        for sid in cp:
            if key in self.local[sid]:
                return self.local[sid][key]

    def _trunc_using(self, using):
        if using is None:
            using = DEFAULT_DB_ALIAS
        using = johnny_settings.DB_CACHE_KEYS[using]
        if len(using) > 100:
            using = using[0:68] + self.keygen.gen_key(using[68:])
        return using

    def set(self, key, val, timeout=None, using=None):
        """
        Set will be using the generational key, so if another thread
        bumps this key, the localstore version will still be invalid.
        If the key is bumped during a transaction it will be new
        to the global cache on commit, so it will still be a bump.
        """
        if timeout is None:
            timeout = self.timeout
        if self.is_managed(using=using) and self._patched_var:
            self.local[key] = val
        else:
            self.cache_backend.set(key, val, timeout)

    def _clear(self, using=None):
        self.local.clear('%s_%s_*' %
                         (self.prefix, self._trunc_using(using)))

    def _flush(self, commit=True, using=None):
        """
        Flushes the internal cache, either to the memcache or rolls back
        """
        if commit:
            # XXX: multi-set?
            if self._uses_savepoints():
                self._commit_all_savepoints(using)
            c = self.local.mget('%s_%s_*' %
                                (self.prefix, self._trunc_using(using)))
            for key, value in c.items():
                self.cache_backend.set(key, value, self.timeout)
        else:
            if self._uses_savepoints():
                self._rollback_all_savepoints(using)
        self._clear(using)
        self._clear_sid_stack(using)

    def _patched(self, original, commit=True, unless_managed=False):
        @wraps(original, assigned=available_attrs(original))
        def newfun(using=None):
            original(using=using)
            # copying behavior of original func
            # if it is an 'unless_managed' version we should do nothing if transaction is managed
            if not unless_managed or not self.is_managed(using=using):
                self._flush(commit=commit, using=using)

        return newfun

    def _uses_savepoints(self):
        return connection.features.uses_savepoints

    def _sid_key(self, sid, using=None):
        if using is not None:
            prefix = 'trans_savepoint_%s' % using
        else:
            prefix = 'trans_savepoint'

        if sid is not None and sid.startswith(prefix):
            return sid
        return '%s_%s'%(prefix, sid)

    def _create_savepoint(self, sid, using=None):
        key = self._sid_key(sid, using)

        #get all local dirty items
        c = self.local.mget('%s_%s_*' %
                            (self.prefix, self._trunc_using(using)))
        #store them to a dictionary in the localstore
        if key not in self.local:
            self.local[key] = {}
        for k, v in c.items():
            self.local[key][k] = v
        #clear the dirty
        self._clear(using)
        #append the key to the savepoint stack
        sids = self._get_sid(using)
        if key not in sids:
            sids.append(key)

    def _rollback_savepoint(self, sid, using=None):
        sids = self._get_sid(using)
        key = self._sid_key(sid, using)
        stack = []
        try:
            popped = None
            while popped != key:
                popped = sids.pop()
                stack.insert(0, popped)
            #delete items from localstore
            for i in stack:
                del self.local[i]
            #clear dirty
            self._clear(using)
        except IndexError:
            #key not found, don't delete from localstore, restore sid stack
            for i in stack:
                sids.insert(0, i)

    def _commit_savepoint(self, sid, using=None):
        # commit is not a commit but is in reality just a clear back to that
        # savepoint and adds the items back to the dirty transaction.
        key = self._sid_key(sid, using)
        sids = self._get_sid(using)
        stack = []
        try:
            popped = None
            while popped != key:
                popped = sids.pop()
                stack.insert(0, popped)
            self._store_dirty(using)
            for i in stack:
                for k, v in self.local.get(i, {}).items():
                    self.local[k] = v
                del self.local[i]
            self._restore_dirty(using)
        except IndexError:
            for i in stack:
                sids.insert(0, i)

    def _commit_all_savepoints(self, using=None):
        sids = self._get_sid(using)
        if sids:
            self._commit_savepoint(sids[0], using)

    def _rollback_all_savepoints(self, using=None):
        sids = self._get_sid(using)
        if sids:
            self._rollback_savepoint(sids[0], using)

    def _store_dirty(self, using=None):
        c = self.local.mget('%s_%s_*' %
                            (self.prefix, self._trunc_using(using)))
        backup = 'trans_dirty_store_%s' % self._trunc_using(using)
        self.local[backup] = {}
        for k, v in c.items():
            self.local[backup][k] = v
        self._clear(using)

    def _restore_dirty(self, using=None):
        backup = 'trans_dirty_store_%s' % self._trunc_using(using)
        for k, v in self.local.get(backup, {}).items():
            self.local[k] = v
        del self.local[backup]

    def _savepoint(self, original):
        @wraps(original, assigned=available_attrs(original))
        def newfun(using=None):
            if using is not None:
                sid = original(using=using)
            else:
                sid = original()
            if self._uses_savepoints():
                self._create_savepoint(sid, using)
            return sid
        return newfun

    def _savepoint_rollback(self, original):
        def newfun(sid, *args, **kwargs):
            original(sid, *args, **kwargs)
            if self._uses_savepoints():
                if len(args) == 2:
                    using = args[1]
                else:
                    using = kwargs.get('using', None)
                self._rollback_savepoint(sid, using)
        return newfun

    def _savepoint_commit(self, original):
        def newfun(sid, *args, **kwargs):
            original(sid, *args, **kwargs)
            if self._uses_savepoints():
                if len(args) == 1:
                    using = args[0]
                else:
                    using = kwargs.get('using', None)
                self._commit_savepoint(sid, using)
        return newfun

    def _getreal(self, name):
        return getattr(transaction, 'real_%s' % name,
                getattr(transaction, name))

    def patch(self):
        """
        This function monkey patches commit and rollback
        writes to the cache should not happen until commit (unless our state
        isn't managed). It does not yet support savepoints.
        """
        if not self._patched_var:
            self._originals['rollback'] = self._getreal('rollback')
            self._originals['rollback_unless_managed'] = self._getreal('rollback_unless_managed')
            self._originals['commit'] = self._getreal('commit')
            self._originals['commit_unless_managed'] = self._getreal('commit_unless_managed')
            self._originals['savepoint'] = self._getreal('savepoint')
            self._originals['savepoint_rollback'] = self._getreal('savepoint_rollback')
            self._originals['savepoint_commit'] = self._getreal('savepoint_commit')
            transaction.rollback = self._patched(transaction.rollback, False)
            transaction.rollback_unless_managed = self._patched(transaction.rollback_unless_managed,
                                                                       False, unless_managed=True)
            transaction.commit = self._patched(transaction.commit, True)
            transaction.commit_unless_managed = self._patched(transaction.commit_unless_managed,
                                                                     True, unless_managed=True)
            transaction.savepoint = self._savepoint(transaction.savepoint)
            transaction.savepoint_rollback = self._savepoint_rollback(transaction.savepoint_rollback)
            transaction.savepoint_commit = self._savepoint_commit(transaction.savepoint_commit)

            self._patched_var = True

    def unpatch(self):
        for fun in self._originals:
            setattr(transaction, fun, self._originals[fun])
        self._patched_var = False
