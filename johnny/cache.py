#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Johnny's main caching functionality."""

import sys
try:
    from functools import wraps
except ImportError:
    from django.utils.functional import wraps  # Python 2.3, 2.4 fallback.
from uuid import uuid4
try:
    from hashlib import md5
except ImportError:
    from md5 import md5

from django.conf import settings 
import localstore
import signals
from transaction import TransactionManager

local = localstore.LocalStore()

def get_backend():
    """Get's a QueryCacheBackend class for the current version of django."""
    import django
    if django.VERSION[:2] == (1, 1):
        return QueryCacheBackend11
    if django.VERSION[:2] == (1, 2):
        return QueryCacheBackend
    raise ImproperlyConfigured("QueryCacheMiddleware cannot patch your version of django.")

def invalidate(*tables, **kwargs):
    """Invalidate the current generation for one or more tables.  The arguments
    can be either strings representing database table names or models.  Pass in
    kwarg 'using' to set the database."""
    backend = get_backend()()
    db = kwargs.get('using', 'default')
    resolve = lambda x: x if isinstance(x, basestring) else x._meta.db_table
    if backend._patched:
        for t in map(resolve, tables):
            backend.keyhandler.invalidate_table(t, db)

# The KeyGen is used only to generate keys.  Some of these keys will be used
# directly in the cache, while others are only general purpose functions to
# generate hashes off of one or more values.

class KeyGen(object):
    """This class is responsible for generating keys."""

    def __init__(self, prefix):
        self.prefix = prefix

    def random_generator(self):
        """Creates a random unique id."""
        return self.gen_key(str(uuid4()))

    def gen_table_key(self, table, db='default'):
        """Returns a key that is standard for a given table name and database alias.
        Total length up to 212 (max for memcache is 250)."""
        table = str(table)
        db = str(db)
        if len(table) > 100:
            table = table[0:68] + self.gen_key(table[68:])
        if db and len(db) > 100:
            db = db[0:68] + self.gen_key(db[68:])
        return '%s_%s_table_%s' % (self.prefix, db, table)

    def gen_multi_key(self, values, db='default'):
        """Takes a list of generations (not table keys) and returns a key."""
        if db and len(db) > 100:
            db = db[0:68] + self.gen_key(db[68:])
        return '%s_%s_multi_%s' % (self.prefix, db, self.gen_key(*values))

    def gen_key(self, *values):
        """Generate a key from one or more values."""
        key = md5()
        for v in values:
            key.update(str(v))
        return key.hexdigest()

class KeyHandler(object):
    """Handles pulling and invalidating the key from from the cache based
    on the table names.  Higher-level logic dealing with johnny cache specific
    keys go in this class."""
    def __init__(self, cache_backend, keygen=KeyGen, prefix=None):
        self.prefix = prefix
        self.keygen = keygen(prefix)
        self.cache_backend = cache_backend

    def get_generation(self, *tables, **kwargs):
        """Get the generation key for any number of tables."""
        db = kwargs.get('db', 'default')
        if len(tables) > 1:
            return self.get_multi_generation(tables, db)
        return self.get_single_generation(tables[0], db)

    def get_single_generation(self, table, db='default'):
        """Creates a random generation value for a single table name"""
        key = self.keygen.gen_table_key(table, db)
        val = self.cache_backend.get(key, None, db)
        if val == None:
            val = self.keygen.random_generator()
            self.cache_backend.set(key, val, 0, db)
        return val

    def get_multi_generation(self, tables, db='default'):
        """Takes a list of table names and returns an aggregate
        value for the generation"""
        generations = []
        for table in tables:
            generations.append(self.get_single_generation(table, db))
        key = self.keygen.gen_multi_key(generations, db)
        val = self.cache_backend.get(key, None, db)
        if val == None:
            val = self.keygen.random_generator()
            self.cache_backend.set(key, val, 0, db)
        return val

    def invalidate_table(self, table, db='default'):
        """Invalidates a table's generation and returns a new one
        (Note that this also invalidates all multi generations
        containing the table)"""
        key = self.keygen.gen_table_key(table, db)
        val = self.keygen.random_generator()
        self.cache_backend.set(key, val, 0, db)
        return val

    def sql_key(self, generation, sql, params, order, result_type, using='default'):
        """Return the specific cache key for the sql query described by the
        pieces of the query and the generation key."""
        # these keys will always look pretty opaque
        key = '%s_%s_query_%s.%s' % (self.prefix, using, generation, self.keygen.gen_key(sql, params,
                order, result_type))
        return key

# TODO: This QueryCacheBackend is for 1.2;  we need to write one for 1.1 as well
# we can test them out by using different virtualenvs pretty quickly

# XXX: Thread safety concerns?  Should we only need to patch once per process?

class QueryCacheBackend(object):
    """This class is the engine behind the query cache. It reads the queries
    going through the django Query and returns from the cache using
    the generation keys, or on a miss from the database and caches the results.
    Each time a model is updated the table keys for that model are re-created,
    invalidating all cached querysets for that model.

    There are different QueryCacheBackend's for different versions of django;
    call ``johnny.cache.get_backend`` to automatically get the proper class.
    """
    __shared_state = {}
    def __init__(self, cache_backend=None, keyhandler=None, keygen=None):
        self.__dict__ = self.__shared_state
        self.prefix = getattr(settings, 'JOHNNY_MIDDLEWARE_KEY_PREFIX', 'jc')
        if keyhandler: self.kh_class = keyhandler
        if keygen: self.kg_class = keygen
        if not cache_backend and not hasattr(self, 'cache_backend'):
            from django.core.cache import cache as cache_backend

        if not keygen and not hasattr(self, 'kg_class'):
            self.kg_class = KeyGen
        if keyhandler is None and not hasattr(self, 'kh_class'):
            self.kh_class = KeyHandler

        if cache_backend:
            self.cache_backend = TransactionManager(cache_backend, self.kg_class)
            self.keyhandler = self.kh_class(self.cache_backend, self.kg_class, self.prefix)
        self._patched = getattr(self, '_patched', False)

    def _monkey_select(self, original):
        from django.db.models.sql import query
        from django.db.models.sql.constants import MULTI
        from django.db.models.sql.datastructures import EmptyResultSet

        @wraps(original)
        def newfun(cls, *args, **kwargs):
            if args:
                result_type = args[0]
            else:
                result_type = kwargs.get('result_type', MULTI)

            from django.db.models.sql import compiler
            if type(cls) in (compiler.SQLInsertCompiler, compiler.SQLDeleteCompiler, compiler.SQLUpdateCompiler):
                return original(cls, *args, **kwargs)
            try:
                sql, params = cls.as_sql()
                if not sql:
                    raise EmptyResultSet
            except EmptyResultSet:
                if result_type == MULTI:
                    return query.empty_iter()
            db = getattr(cls, 'using', 'default')
            gen_key = self.keyhandler.get_generation(*cls.query.tables, **{'db':db})
            key = self.keyhandler.sql_key(gen_key, sql, params, cls.get_ordering(), result_type, db)
            val = self.cache_backend.get(key, None, db)

            if val is not None:
                signals.qc_hit.send(sender=cls, tables=cls.query.tables,
                        query=(sql, params, cls.query.ordering_aliases),
                        size=len(val), key=key)
                return val

            signals.qc_miss.send(sender=cls, tables=cls.query.tables,
                    query=(sql, params, cls.query.ordering_aliases),
                    key=key)

            val = original(cls, *args, **kwargs)

            if hasattr(val, '__iter__'):
                #Can't permanently cache lazy iterables without creating
                #a cacheable data structure. Note that this makes them
                #no longer lazy...
                #todo - create a smart iterable wrapper
                val = list(val)
            self.cache_backend.set(key, val, 0, db)
            return val
        return newfun

    def _monkey_write(self, original):
        @wraps(original)
        def newfun(cls, *args, **kwargs):
            db = getattr(cls, 'using', 'default')
            from django.db.models.sql import compiler
            if type(cls) == compiler.SQLInsertCompiler:
                #Inserts are a special case where cls.tables
                #are not populated.
                tables = [cls.query.model._meta.db_table]
            else:
                tables = cls.query.tables
            for table in tables:
                self.keyhandler.invalidate_table(table, db)
            return original(cls, *args, **kwargs)
        return newfun


    def patch(self):
        """monkey patches django.db.models.sql.compiler.SQL*Compiler series"""
        if not self._patched:
            from django.db.models.sql import compiler
            self._original = {}
            for reader in (compiler.SQLCompiler, compiler.SQLAggregateCompiler, compiler.SQLDateCompiler):
                self._original[reader] = reader.execute_sql
                reader.execute_sql = self._monkey_select(reader.execute_sql)
            for updater in (compiler.SQLInsertCompiler, compiler.SQLDeleteCompiler, compiler.SQLUpdateCompiler):
                self._original[updater] = updater.execute_sql
                updater.execute_sql = self._monkey_write(updater.execute_sql)
            self._patched = True
            self.cache_backend.patch()
            self._handle_signals()

    def unpatch(self):
        """un-applies this patch."""
        if not self._patched:
            return
        from django.db.models.sql import compiler
        for func in (compiler.SQLCompiler, compiler.SQLAggregateCompiler, compiler.SQLDateCompiler,
                compiler.SQLInsertCompiler, compiler.SQLDeleteCompiler, compiler.SQLUpdateCompiler):
            func.execute_sql = self._original[func]
        self.cache_backend.unpatch()
        self._patched = False

    def invalidate_m2m(self, instance, **kwargs):
        if self._patched:
            self.keyhandler.invalidate_table(instance)
    def invalidate(self, instance, **kwargs):
        if self._patched:
            self.keyhandler.invalidate_table(instance._meta.db_table)

    def _handle_signals(self):
        from django.db.models import signals
        signals.post_save.connect(self.invalidate, sender=None)
        signals.post_delete.connect(self.invalidate, sender=None)
        import signals as johnny_signals
        johnny_signals.qc_m2m_change.connect(self.invalidate_m2m, sender=None)

    def flush_query_cache(self):
        from django.db import connection
        tables = connection.introspection.table_names()
        #seen_models = connection.introspection.installed_models(tables)
        for table in tables:
            self.keyhandler.invalidate_table(table)

class QueryCacheBackend11(QueryCacheBackend):
    """This is the 1.1.x version of the QueryCacheBackend.  In Django1.1, we
    patch django.db.models.sql.query.Query.execute_sql to implement query
    caching.  Usage across QueryCacheBackends is identical."""
    __shared_state = {}
    def _monkey_execute_sql(self, original):
        from django.db.models.sql import query
        from django.db.models.sql.constants import MULTI, SINGLE
        from django.db.models.sql.datastructures import EmptyResultSet

        @wraps(original)
        def newfun(cls, result_type=MULTI):
            try:
                sql, params = cls.as_sql()
                if not sql:
                    raise EmptyResultSet
            except EmptyResultSet:
                if result_type == MULTI:
                    return query.empty_iter()

            # get the cache key for the current generation + this query set
            if cls.tables: # on INSERT statements, this isn't set...
                gen_key = self.keyhandler.get_generation(*cls.tables)
                key = self.keyhandler.sql_key(gen_key, sql, params,
                        cls.ordering_aliases, result_type)
                val = self.cache_backend.get(key, None)

                if val is not None:
                    signals.qc_hit.send(sender=cls, tables=cls.tables,
                            query=(sql, params, cls.ordering_aliases),
                            size=len(val), key=key)
                    return val
                signals.qc_miss.send(sender=cls, tables=cls.tables,
                        query=(sql, params, cls.ordering_aliases),
                        key=key)

            # we didn't find the value in the cache, so execute the query
            result = original(cls, result_type)
            if cls.tables and not sql.startswith('UPDATE') and not sql.startswith('DELETE'):
                result = list(result)
                self.cache_backend.set(key, result)
            return result
        return newfun

    def patch(self):
        from django.db.models import sql
        from django.db.models.fields import related
        if self._patched:
            return
        self._original = sql.Query.execute_sql
        self._original_m2m = related.create_many_related_manager
        sql.Query.execute_sql = self._monkey_execute_sql(sql.Query.execute_sql)
        related.create_many_related_manager = self._patched_m2m(related.create_many_related_manager)
        self._handle_signals()
        self.cache_backend.patch()
        self._patched = True

    def unpatch(self):
        from django.db.models import sql
        if not self._patched:
            return
        sql.Query.execute_sql = self._original
        self.cache_backend.unpatch()
        self._patched = False

    def _patched_m2m_func(self, original):
        def f(cls, *args, **kwargs):
            val = original(cls, *args, **kwargs)
            signals.qc_m2m_change.send(sender=cls, instance=cls.join_table.strip('"').strip('`'))
            return val
        return f

    def _patched_m2m(self, original):
        def f(*args, **kwargs):
            related_manager = original(*args, **kwargs)
            if getattr(related_manager, '_johnny_patched', None):
                return related_manager
            for i in ('add', 'remove', 'clear'):
                item = '_%s_items'%i
                setattr(related_manager, item,
                        self._patched_m2m_func(getattr(related_manager, item))
                       )
            related_manager._johnny_patched = True
            return related_manager
        return f
