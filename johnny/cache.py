#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Johnny's main caching functionality."""

import sys
from functools import wraps
from uuid import uuid4
try:
    from hashlib import md5
except ImportError:
    from md5 import md5

# The KeyGen is used only to generate keys.  Some of these keys will be used
# directly in the cache, while others are only general purpose functions to
# generate hashes off of one or more values.

class KeyGen(object):
    """This class is responsible for generating keys."""

    def random_generator(self):
        """Creates a random unique id."""
        return self.gen_key(str(uuid4()))

    def gen_table_key(self, table):
        """Returns a key that is standard for a given table name.
        Total length up to 242 (max for memcache is 250)."""
        if len(table) > 200:
            table = table[0:200] + self.gen_key(table[200:])
        return 'jc_table_%s' % str(table)

    def gen_multi_key(self, values):
        """Takes a list of generations (not table keys) and returns a key."""
        return 'jc_multi_%s' % self.gen_key(*values)

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
    def __init__(self, cache_backend, keygen=KeyGen):
        self.keygen = keygen()
        self.cache_backend = cache_backend

    def get_generation(self, *tables):
        """Get the generation key for any number of tables."""
        if len(tables) > 1:
            return self.get_multi_generation(tables)
        return self.get_single_generation(tables[0])

    def get_single_generation(self, table):
        """Creates a random generation value for a single table name"""
        key = self.keygen.gen_table_key(table)
        val = self.cache_backend.get(key, None)
        if val == None:
            val = self.keygen.random_generator()
            self.cache_backend.set(key, val)
        return val

    def get_multi_generation(self, tables):
        """Takes a list of table names and returns an aggregate
        value for the generation"""
        generations = []
        for table in tables:
            generations += self.get_single_generation(table)
        key = self.keygen.gen_multi_key(generations)
        val = self.cache_backend.get(key, None)
        if val == None:
            val = self.keygen.random_generator()
            self.cache_backend.set(key, val)
        return val

    def invalidate_table(self, table):
        """Invalidates a table's generation and returns a new one
        (Note that this also invalidates all multi generations
        containing the table)"""
        key = self.keygen.gen_table_key(table)
        val = self.keygen.random_generator()
        self.cache_backend.set(key, val)
        return val

    def sql_key(self, generation, sql, params, order, result_type):
        """Return the specific cache key for the sql query described by the
        pieces of the query and the generation key."""
        # these keys will always look pretty opaque
        key = 'jc_query_%s.%s' % (generation, self.keygen.gen_key(sql, params,
                order, result_type))
        return key

# TODO: This QueryCacheBackend is for 1.2;  we need to write one for 1.1 as well
# we can test them out by using different virtualenvs pretty quickly

# XXX: Thread safety concerns?  Should we only need to patch once per process?

class QueryCacheBackend(object):
    """This class is engine behind the query cache. It reads the queries
    going through the django Query and returns from the cache using
    the generation keys, otherwise from the database and caches the results.
    Each time a model is update the keys are regenerated in the cache
    invalidation the cache for that model and all dependent queries.
    Note that this version of the QueryCacheBackend is for django 1.2; the
    QueryCacheMiddleware automatically selects the right QueryCacheBackend."""
    __shared_state = {}
    def __init__(self, cache_backend, keyhandler=KeyHandler, keygen=KeyGen):
        self.__dict__ = self.__shared_state
        self.keyhandler= keyhandler(cache_backend, keygen)
        self.cache_backend = cache_backend
        self._patched = getattr(self, '_patched', False)

    def _monkey_select(self, original):
        from django.db.models.sql import query
        from django.db.models.sql.constants import MULTI, SINGLE
        from django.db.models.sql.datastructures import EmptyResultSet

        @wraps(original)
        def newfun(cls, result_type=MULTI, *args, **kwargs):
            from django.db.models.sql import compiler
            if type(cls) in (compiler.SQLInsertCompiler, compiler.SQLDeleteCompiler, compiler.SQLUpdateCompiler):
                return original(cls, result_type, *args, **kwargs)
            try:
                sql, params = cls.as_sql()
                if not sql:
                    raise EmptyResultSet
            except EmptyResultSet:
                if result_type == MULTI:
                    return query.empty_iter()

            gen_key = self.keyhandler.get_generation(*cls.query.tables)
            key = self.keyhandler.sql_key(gen_key, sql, params, cls.get_ordering(), result_type)
            val = self.cache_backend.get(key, None)
            if val != None:
                return val
            else:
                val = original(cls, result_type, *args, **kwargs)
                if hasattr(val, '__iter__'):
                    #Can't permanently cache lazy iterables without creating
                    #a cacheable data structure. Note that this makes them
                    #no longer lazy...
                    #todo - create a smart iterable wrapper
                    val = list(val)
                self.cache_backend.set(key, val)
            return val
        return newfun

    def _monkey_write(self, original):
        @wraps(original)
        def newfun(cls, *args, **kwargs):
            from django.db.models.sql import compiler
            if type(cls) == compiler.SQLInsertCompiler:
                tables = [cls.query.model._meta.db_table]
            else:
                tables = cls.query.tables
            for table in tables:
                self.keyhandler.invalidate_table(table)
            try:
                return original(cls, *args, **kwargs)
            except:
                import pdb
                pdb.set_trace()
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

    def unpatch(self):
        """un-applies this patch."""
        if not self._patched:
            return
        from django.db.models.sql import compiler
        for func in (compiler.SQLCompiler, compiler.SQLAggregateCompiler, compiler.SQLDateCompiler,
                compiler.SQLInsertCompiler, compiler.SQLDeleteCompiler, compiler.SQLUpdateCompiler):
            func.execute_compiler = self._original[func]
        self._patched = False

    def invalidate(self, instance, **kwargs):
        if self._patched:
            self.keyhandler.invalidate_table(instance._meta.db_table)

    def _handle_signals(self):
        from django.db.models import signals
        signals.post_save.connect(self.invalidate, sender=None)
        signals.post_delete.connect(self.invalidate, sender=None)

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
                    # the ordering_aliases is a special path in the original code,
                    # but we're including it in our key above.. is that enough?
                    return val
                    #if not (cls.ordering_aliases and result_type == SINGLE):
                    #    return val

                # we didn't find the value in the cache, so execute the query
            # uncomment below to make sure that only INSERTs are bypassing cache
            elif sql.startswith('INSERT') and 'django_content_type' in sql:
                pass #from ipdb import set_trace; set_trace()

            cursor = cls.connection.cursor()
            cursor.execute(sql, params)

            if not result_type:
                return cursor
            if result_type == SINGLE:
                if cls.ordering_aliases:
                    return cursor.fetchone()[:-len(cls.ordering_aliases)]
                # otherwise, cache the value and return
                result = cursor.fetchone()
                self.cache_backend.set(key, result)
                return result
            #from ipdb import set_trace; set_trace()

            if cls.ordering_aliases:
                result = query.order_modified_iter(cursor, len(cls.ordering_aliases),
                        cls.connection.features.empty_fetchmany_value)
            else:
                result = iter((lambda: cursor.fetchmany(query.GET_ITERATOR_CHUNK_SIZE)),
                        cls.connection.features.empty_fetchmany_value)
            # XXX: We skip the chunked reads issue here because we want to put
            # the query result into the cache;  however, is there a way we could
            # provide an iter that would cache automatically upon read?  Would
            # this less-greedy caching strategy actually be worse in the common case?
            if cls.tables:
                result = list(result)
                self.cache_backend.set(key, result)
            return result
        return newfun

    def patch(self):
        from django.db.models import sql
        if self._patched:
            return
        #print "Patching execute_sql (1.1)"
        self._original = sql.Query.execute_sql
        sql.Query.execute_sql = self._monkey_execute_sql(sql.Query.execute_sql)
        self._handle_signals()
        self._patched = True

    def unpatch(self):
        from django.db.models import sql
        if not self._patched:
            return
        #print "Unpatching execute_sql (1.1)"
        sql.Query.execute_sql = self._original
        self._patched = False


