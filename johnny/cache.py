from uuid import uuid4
try:
    from hashlib import md5
except:
    from md5 import md5

class KeyGen(object):
    """This class is responsible for creating the QueryCache keys
    for tables."""

    def random_generator(self):
        #creates a random unique id
        key = md5()
        rand = str(uuid4())
        key.update(rand)
        return key.hexdigest()

    def gen_table_key(self, table):
        """Returns a key that is standard for a table name
        Total length up to 242 (max for memcache is 250)"""
        if len(table) > 200:
            m = md5()
            m.update(table[200:])
            table = table[0:200] + m.hexdigest()
        return 'jc_table_%s'%str(table)

    def gen_multi_key(self, values):
        """Takes a list of generations (not table keys) and returns a key""""
        key = md5()
        for v in values:
            key.update(str(v))
        return 'jc_multi_%s'%v.hexdigest()

class KeyHandler(object):
    """Handles pulling and invalidating the key from
    from the cache based on the table names."""
    def __init__(self, cache_backend, keygen=KeyGen):
        self.keygen = keygen()
        self.cache_backend = cache_backend

    def get_table_generation(self, table):
        """Creates a random generation value for a table name"""
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
            generations += self.get_table_generation(table)
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

class QueryCacheBackend(object):
    """This class is engine behind the query cache. It reads the queries
    going through the django Query and returns from the cache using
    the generation keys, otherwise from the database and caches the results.
    Each time a model is update the keys are regenerated in the cache
    invalidation the cache for that model and all dependent queries."""
    def __init__(self, cache_backend, keyhandler=KeyHandler, keygen=KeyGen):
        self.keyhandler= keyhandler(keygen())
        self.cache_backend = cache_backend
        self._patched = False

    def _monkey_select(self, original):
        def newfun(cl, *args, **kwargs):
            tables = cl.query.tables
            if len(tables) == 1:
                key = self.keyhandler.get_table_generation(tables[0])
            else:
                key = self.keyhandler.get_multi_generation(tables)

            val = self.cache_backend.get(key, None)
            if val != None:
                return val
            else:
                val = original(cl, *args, **kwargs)
                if hasattr(val, '__iter__'):
                    #Can't permanently cache lazy iterables
                    val = [i for i in val]
                self.cache_backend.set(key, val)
            return val
        return newfun

    def _monkey_write(self, original):
        def newfun(cl, *args, **kwargs):
            tables = cl.query.tables
            for table in tables:
                self.keyhandler.invalidate_table(table)
            return original(cl, *args, **kwargs)
        return newfun


    def patch(self):
        """monkey patches django.db.models.sql.compiler.SQL*Compiler series"""
        if not self._patched:
            from django.db.models import sql
            for reader in (sql.SQLCompiler, sql.SQLAggregateCompiler, sql.DateCompiler):
                reader.execute_sql = self._monkey_select(reader.execute_sql)
            for updater in (sql.SQLInsertCompiler, sql.SQLDeleteCompiler, sql.SQLUpdateCompiler):
                updater.execute_sql = self._monkey_write(updater.execute_sql)
            self.patched = True

