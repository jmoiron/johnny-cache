import django
from django.db import transaction as django_transaction
from django.db import connection
try:
    from django.db import DEFAULT_DB_ALIAS
except:
    DEFUALT_DB_ALIAS = None

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
        if self.has_multi_db():
            if using is None:
                using = DEFAULT_DB_ALIAS
        else:
            using = 'default'
        if using not in d:
            d[using] = []
        return d[using]

    def _clear_sid_stack(self, using=None):
        if self.has_multi_db():
            if using is None:
                using = DEFAULT_DB_ALIAS
        else:
            using = 'default'
        if using in self.local.get('trans_sids', {}):
            del self.local['trans_sids']

    def has_multi_db(self):
        if django.VERSION[:2] > (1, 1):
            return True
        return False

    def is_managed(self):
        return django_transaction.is_managed()

    def get(self, key, default=None, using=None):
        if self.is_managed() and self._patched_var:
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
        if self.has_multi_db():
            if using is None:
                using = DEFAULT_DB_ALIAS
        else:
            using = 'default'
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
        if self.is_managed() and self._patched_var:
            self.local[key] = val
        else:
            self.cache_backend.set(key, val, timeout)

    def _clear(self, using=None):
        if self.has_multi_db():
            self.local.clear('%s_%s_*' %
                             (self.prefix, self._trunc_using(using)))
        else:
            self.local.clear('%s_*' % self.prefix)

    def _flush(self, commit=True, using=None):
        """
        Flushes the internal cache, either to the memcache or rolls back
        """
        if commit:
            # XXX: multi-set?
            if self._uses_savepoints():
                self._commit_all_savepoints(using)
            if self.has_multi_db():
                c = self.local.mget('%s_%s_*' %
                                    (self.prefix, self._trunc_using(using)))
            else:
                c = self.local.mget('%s_*' % self.prefix)
            for key, value in c.iteritems():
                self.cache_backend.set(key, value, self.timeout)
        else:
            if self._uses_savepoints():
                self._rollback_all_savepoints(using)
        self._clear(using)
        self._clear_sid_stack(using)

    def _patched(self, original, commit=True):
        @wraps(original, assigned=available_attrs(original))
        def newfun(using=None):
            #1.2 version
            original(using=using)
            self._flush(commit=commit, using=using)

        @wraps(original, assigned=available_attrs(original))
        def newfun11():
            #1.1 version
            original()
            self._flush(commit=commit)

        if django.VERSION[:2] == (1, 1):
            return newfun11
        elif django.VERSION[:2] > (1, 1):
            return newfun
        return original

    def _uses_savepoints(self):
        return connection.features.uses_savepoints

    def _sid_key(self, sid, using=None):
        if using is not None:
            prefix = 'trans_savepoint_%s' % using
        else:
            prefix = 'trans_savepoint'

        if sid.startswith(prefix):
            return sid
        return '%s_%s'%(prefix, sid)

    def _create_savepoint(self, sid, using=None):
        key = self._sid_key(sid, using)

        #get all local dirty items
        if self.has_multi_db():
            c = self.local.mget('%s_%s_*' %
                                (self.prefix, self._trunc_using(using)))
        else:
            c = self.local.mget('%s_*' % self.prefix)
        #store them to a dictionary in the localstore
        if key not in self.local:
            self.local[key] = {}
        for k, v in c.iteritems():
            self.local[key][k] = v
        #clear the dirty
        self._clear(using)
        #append the key to the savepoint stack
        sids = self._get_sid(using)
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
                for k, v in self.local[i].iteritems():
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
        if self.has_multi_db():
            c = self.local.mget('%s_%s_*' %
                                (self.prefix, self._trunc_using(using)))
        else:
            c = self.local.mget('%s_*' % self.prefix)
        backup = 'trans_dirty_store_%s' % self._trunc_using(using)
        self.local[backup] = {}
        for k, v in c.iteritems():
            self.local[backup][k] = v
        self._clear(using)

    def _restore_dirty(self, using=None):
        backup = 'trans_dirty_store_%s' % self._trunc_using(using)
        for k, v in self.local.get(backup, {}).iteritems():
            self.local[k] = v
        del self.local[backup]

    def _savepoint(self, original):
        @wraps(original, assigned=available_attrs(original))
        def newfun(using=None):
            if using != None:
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
        return getattr(django_transaction, 'real_%s' % name,
                getattr(django_transaction, name))

    def patch(self):
        """
        This function monkey patches commit and rollback
        writes to the cache should not happen until commit (unless our state
        isn't managed). It does not yet support savepoints.
        """
        if not self._patched_var:
            self._originals['rollback'] = self._getreal('rollback')
            self._originals['commit'] = self._getreal('commit')
            self._originals['savepoint'] = self._getreal('savepoint')
            self._originals['savepoint_rollback'] = self._getreal('savepoint_rollback')
            self._originals['savepoint_commit'] = self._getreal('savepoint_commit')
            django_transaction.rollback = self._patched(django_transaction.rollback, False)
            django_transaction.commit = self._patched(django_transaction.commit, True)
            django_transaction.savepoint = self._savepoint(django_transaction.savepoint)
            django_transaction.savepoint_rollback = self._savepoint_rollback(django_transaction.savepoint_rollback)
            django_transaction.savepoint_commit = self._savepoint_commit(django_transaction.savepoint_commit)

            self._patched_var = True

    def unpatch(self):
        for fun in self._originals:
            setattr(django_transaction, fun, self._originals[fun])
        self._patched_var = False
