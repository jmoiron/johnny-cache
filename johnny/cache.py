"""Johnny's main caching functionality."""

from hashlib import md5
from uuid import uuid4

import django
from django.db.models.signals import post_save, post_delete

from . import localstore, signals
from . import settings
from .compat import (
    force_bytes, force_text, string_types, text_type, empty_iter)
from .decorators import wraps, available_attrs
from .transaction import TransactionManager


class NotInCache(object):
    #This is used rather than None to properly cache empty querysets
    pass

no_result_sentinel = "22c52d96-156a-4638-a38d-aae0051ee9df"
local = localstore.LocalStore()


def disallowed_table(*tables):
    """Returns True if a set of tables is in the blacklist or, if a whitelist is set,
    any of the tables is not in the whitelist. False otherwise."""
    # XXX: When using a black or white list, this has to be done EVERY query;
    # It'd be nice to make this as fast as possible.  In general, queries
    # should have relatively few tables involved, and I don't imagine that
    # blacklists would grow very vast.  The fastest i've been able to come
    # up with is to pre-create a blacklist set and use intersect.
    return not bool(settings.WHITELIST.issuperset(tables)) if settings.WHITELIST\
        else bool(settings.BLACKLIST.intersection(tables))


def get_backend(**kwargs):
    """
    Get's a QueryCacheBackend object for the given options and current
    version of django.  If no arguments are given, and a QCB has been
    created previously, ``get_backend`` returns that.  Otherwise,
    ``get_backend`` will return the default backend.
    """
    cls = QueryCacheBackend
    return cls(**kwargs)

def enable():
    """Enable johnny-cache, for use in scripts, management commands, async
    workers, or other code outside the django request flow."""
    get_backend().patch()

def disable():
    """Disable johnny-cache.  This will disable johnny-cache for the whole
    process, and if writes happen during the time where johnny is disabled,
    tables will not be invalidated properly.  Use Carefully."""
    get_backend().unpatch()

patch,unpatch = enable,disable

def resolve_table(x):
    """Return a table name for x, where x is either a model instance or a string."""
    if isinstance(x, string_types):
        return x
    return x._meta.db_table


def invalidate(*tables, **kwargs):
    """Invalidate the current generation for one or more tables.  The arguments
    can be either strings representing database table names or models.  Pass in
    kwarg ``using`` to set the database."""
    backend = get_backend()
    db = kwargs.get('using', 'default')

    if backend._patched:
        for t in map(resolve_table, tables):
            backend.keyhandler.invalidate_table(t, db)


def get_tables_for_query(query):
    """
    Takes a Django 'query' object and returns all tables that will be used in
    that query as a list.  Note that where clauses can have their own
    querysets with their own dependent queries, etc.
    """
    from django.db.models.sql.where import WhereNode, SubqueryConstraint
    from django.db.models.query import QuerySet
    tables = [v[0] for v in getattr(query,'alias_map',{}).values()]

    def get_sub_query_tables(node):
        query = node.query_object
        if not hasattr(query, 'field_names'):
            query = query.values(*node.targets)
        else:
            query = query._clone()
        query = query.query
        return [v[0] for v in getattr(query, 'alias_map',{}).values()]

    def get_tables(node, tables):
        if isinstance(node, SubqueryConstraint):
            return get_sub_query_tables(node)
        for child in node.children:
            if isinstance(child, WhereNode):  # and child.children:
                tables = get_tables(child, tables)
            elif not hasattr(child, '__iter__'):
                continue
            else:
                for item in (c for c in child if isinstance(c, QuerySet)):
                    tables += get_tables_for_query(item.query)
        return tables

    if query.where and query.where.children:
        where_nodes = [c for c in query.where.children if isinstance(c, (WhereNode, SubqueryConstraint))]
        for node in where_nodes:
            tables += get_tables(node, tables)

    return list(set(tables))

def get_tables_for_query_pre_16(query):
    """
    Takes a Django 'query' object and returns all tables that will be used in
    that query as a list.  Note that where clauses can have their own
    querysets with their own dependent queries, etc.
    """
    from django.db.models.sql.where import WhereNode
    from django.db.models.query import QuerySet
    tables = [v[0] for v in getattr(query,'alias_map',{}).values()]

    def get_tables(node, tables):
        for child in node.children:
            if isinstance(child, WhereNode):  # and child.children:
                tables = get_tables(child, tables)
            elif not hasattr(child, '__iter__'):
                continue
            else:
                for item in (c for c in child if isinstance(c, QuerySet)):
                    tables += get_tables_for_query(item.query)
        return tables

    if query.where and query.where.children:
        where_nodes = [c for c in query.where.children if isinstance(c, WhereNode)]
        for node in where_nodes:
            tables += get_tables(node, tables)

    return list(set(tables))


if django.VERSION[:2] < (1, 6):
    get_tables_for_query = get_tables_for_query_pre_16


# The KeyGen is used only to generate keys.  Some of these keys will be used
# directly in the cache, while others are only general purpose functions to
# generate hashes off of one or more values.

class KeyGen(object):
    """This class is responsible for generating keys."""

    def __init__(self, prefix):
        self.prefix = prefix

    def random_generator(self):
        """Creates a random unique id."""
        return self.gen_key(force_bytes(uuid4()))

    def gen_table_key(self, table, db='default'):
        """
        Returns a key that is standard for a given table name and database
        alias. Total length up to 212 (max for memcache is 250).
        """
        table = force_text(table)
        db = force_text(settings.DB_CACHE_KEYS[db])
        if len(table) > 100:
            table = table[0:68] + self.gen_key(table[68:])
        if db and len(db) > 100:
            db = db[0:68] + self.gen_key(db[68:])
        return '%s_%s_table_%s' % (self.prefix, db, table)

    def gen_multi_key(self, values, db='default'):
        """Takes a list of generations (not table keys) and returns a key."""
        db = settings.DB_CACHE_KEYS[db]
        if db and len(db) > 100:
            db = db[0:68] + self.gen_key(db[68:])
        return '%s_%s_multi_%s' % (self.prefix, db, self.gen_key(*values))

    @staticmethod
    def _convert(x):
        if isinstance(x, text_type):
            return x.encode('utf-8')
        return force_bytes(x)

    @staticmethod
    def _recursive_convert(x, key):
        for item in x:
            if isinstance(item, (tuple, list)):
                KeyGen._recursive_convert(item, key)
            else:
                key.update(KeyGen._convert(item))

    def gen_key(self, *values):
        """Generate a key from one or more values."""
        key = md5()
        KeyGen._recursive_convert(values, key)
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
        #if local.get('in_test', None): print force_bytes(val).ljust(32), key
        if val is None:
            val = self.keygen.random_generator()
            self.cache_backend.set(key, val, settings.MIDDLEWARE_SECONDS, db)
        return val

    def get_multi_generation(self, tables, db='default'):
        """Takes a list of table names and returns an aggregate
        value for the generation"""
        generations = []
        for table in tables:
            generations.append(self.get_single_generation(table, db))
        key = self.keygen.gen_multi_key(generations, db)
        val = self.cache_backend.get(key, None, db)
        #if local.get('in_test', None): print force_bytes(val).ljust(32), key
        if val is None:
            val = self.keygen.random_generator()
            self.cache_backend.set(key, val, settings.MIDDLEWARE_SECONDS, db)
        return val

    def invalidate_table(self, table, db='default'):
        """Invalidates a table's generation and returns a new one
        (Note that this also invalidates all multi generations
        containing the table)"""
        key = self.keygen.gen_table_key(table, db)
        val = self.keygen.random_generator()
        self.cache_backend.set(key, val, settings.MIDDLEWARE_SECONDS, db)
        return val

    def sql_key(self, generation, sql, params, order, result_type,
                using='default'):
        """
        Return the specific cache key for the sql query described by the
        pieces of the query and the generation key.
        """
        # these keys will always look pretty opaque
        suffix = self.keygen.gen_key(sql, params, order, result_type)
        using = settings.DB_CACHE_KEYS[using]
        return '%s_%s_query_%s.%s' % (self.prefix, using, generation, suffix)


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
        self.prefix = settings.MIDDLEWARE_KEY_PREFIX
        if keyhandler:
            self.kh_class = keyhandler
        if keygen:
            self.kg_class = keygen
        if not cache_backend and not hasattr(self, 'cache_backend'):
            cache_backend = settings._get_backend()

        if not keygen and not hasattr(self, 'kg_class'):
            self.kg_class = KeyGen
        if keyhandler is None and not hasattr(self, 'kh_class'):
            self.kh_class = KeyHandler

        if cache_backend:
            self.cache_backend = TransactionManager(cache_backend,
                                                    self.kg_class)
            self.keyhandler = self.kh_class(self.cache_backend,
                                            self.kg_class, self.prefix)
        self._patched = getattr(self, '_patched', False)

    def _monkey_select(self, original):
        from django.db.models.sql.constants import MULTI
        from django.db.models.sql.datastructures import EmptyResultSet

        @wraps(original, assigned=available_attrs(original))
        def newfun(cls, *args, **kwargs):
            if args:
                result_type = args[0]
            else:
                result_type = kwargs.get('result_type', MULTI)

            if any([isinstance(cls, c) for c in self._write_compilers]):
                return original(cls, *args, **kwargs)
            try:
                sql, params = cls.as_sql()
                if not sql:
                    raise EmptyResultSet
            except EmptyResultSet:
                if result_type == MULTI:
                    return empty_iter()
                else:
                    return

            db = getattr(cls, 'using', 'default')
            key, val = None, NotInCache()
            # check the blacklist for any of the involved tables;  if it's not
            # there, then look for the value in the cache.
            tables = get_tables_for_query(cls.query)
            # if the tables are blacklisted, send a qc_skip signal
            blacklisted = disallowed_table(*tables)

            try:
                ordering_aliases = cls.ordering_aliases
            except AttributeError:
                ordering_aliases = cls.query.ordering_aliases

            if blacklisted:
                signals.qc_skip.send(sender=cls, tables=tables,
                    query=(sql, params, ordering_aliases),
                    key=key)
            if tables and not blacklisted:
                gen_key = self.keyhandler.get_generation(*tables, **{'db': db})
                key = self.keyhandler.sql_key(gen_key, sql, params,
                                              cls.get_ordering(),
                                              result_type, db)
                val = self.cache_backend.get(key, NotInCache(), db)

            if not isinstance(val, NotInCache):
                if val == no_result_sentinel:
                    val = []

                signals.qc_hit.send(sender=cls, tables=tables,
                        query=(sql, params, ordering_aliases),
                        size=len(val), key=key)
                return val

            if not blacklisted:
                signals.qc_miss.send(sender=cls, tables=tables,
                    query=(sql, params, ordering_aliases),
                    key=key)

            val = original(cls, *args, **kwargs)

            if hasattr(val, '__iter__'):
                #Can't permanently cache lazy iterables without creating
                #a cacheable data structure. Note that this makes them
                #no longer lazy...
                #todo - create a smart iterable wrapper
                val = list(val)
            if key is not None:
                if not val:
                    self.cache_backend.set(key, no_result_sentinel, settings.MIDDLEWARE_SECONDS, db)
                else:
                    self.cache_backend.set(key, val, settings.MIDDLEWARE_SECONDS, db)
            return val
        return newfun

    def _monkey_write(self, original):
        @wraps(original, assigned=available_attrs(original))
        def newfun(cls, *args, **kwargs):
            db = getattr(cls, 'using', 'default')
            from django.db.models.sql import compiler
            # we have to do this before we check the tables, since the tables
            # are actually being set in the original function
            ret = original(cls, *args, **kwargs)

            if isinstance(cls, compiler.SQLInsertCompiler):
                #Inserts are a special case where cls.tables
                #are not populated.
                tables = [cls.query.model._meta.db_table]
            else:
                #if cls.query.tables != list(cls.query.table_map):
                #    pass
                #tables = list(cls.query.table_map)
                tables = cls.query.tables
            for table in tables:
                if not disallowed_table(table):
                    self.keyhandler.invalidate_table(table, db)
            return ret
        return newfun

    def patch(self):
        """
        monkey patches django.db.models.sql.compiler.SQL*Compiler series
        """
        from django.db.models.sql import compiler

        self._read_compilers = (
            compiler.SQLCompiler,
            compiler.SQLAggregateCompiler,
            compiler.SQLDateCompiler,
        )
        self._write_compilers = (
            compiler.SQLInsertCompiler,
            compiler.SQLDeleteCompiler,
            compiler.SQLUpdateCompiler,
        )
        if not self._patched:
            self._original = {}
            for reader in self._read_compilers:
                self._original[reader] = reader.execute_sql
                reader.execute_sql = self._monkey_select(reader.execute_sql)
            for updater in self._write_compilers:
                self._original[updater] = updater.execute_sql
                updater.execute_sql = self._monkey_write(updater.execute_sql)
            self._patched = True
            self.cache_backend.patch()
            self._handle_signals()

    def unpatch(self):
        """un-applies this patch."""
        if not self._patched:
            return
        for func in self._read_compilers + self._write_compilers:
            func.execute_sql = self._original[func]
        self.cache_backend.unpatch()
        self._patched = False

    def invalidate(self, instance, **kwargs):
        if self._patched:
            table = resolve_table(instance)
            using = kwargs.get('using', 'default')
            if not disallowed_table(table):
                self.keyhandler.invalidate_table(table, db=using)

            tables = set()
            tables.add(table)

            try:
                 instance._meta._related_objects_cache
            except AttributeError:
                 instance._meta._fill_related_objects_cache()

            for obj in instance._meta._related_objects_cache.keys():
                obj_table = obj.model._meta.db_table
                if obj_table not in tables:
                    tables.add(obj_table)
                    if not disallowed_table(obj_table):
                        self.keyhandler.invalidate_table(obj_table)

    def _handle_signals(self):
        post_save.connect(self.invalidate, sender=None)
        post_delete.connect(self.invalidate, sender=None)

    def flush_query_cache(self):
        from django.db import connection
        tables = connection.introspection.table_names()
        #seen_models = connection.introspection.installed_models(tables)
        for table in tables:
            # we want this to just work, so invalidate even things in blacklist
            self.keyhandler.invalidate_table(table)
