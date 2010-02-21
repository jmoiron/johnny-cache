.. queryset cache main documentation, including options, enabling/disabling,
   using with raw sql and cursors, signals, etc

The QuerySet Cache
==================

QuerySet caching is the automatic caching of all database reads.  Conceptually, 
it works very similar to the built-in write-invalidate queryset caching that 
is present in your RDBMS.  Although it is not typically required to modify,
it is located in ``johnny.cache``.

When a read (``SELECT``) is made from one or more tables, that read is cached. 
When a write (``INSERT``, ``UPDATE``, etc) is made against that table, the 
read cache built up for that table is invalidated.  The way that Johnny 
achieves this is through the use of generational keys:

* every table in your application gets a "key" associated with it that
  corresponds to the current *generation* of data
* reads are cached with keys based off of the generations of the tables being
  read from
* when a write is performed, the generation key for all involved tables is
  modified

When the generation key is modified, any cache keys previously built against
prior generations are no longer recoverable, since the old generation key is
now lost.  This means on an LRU cache (like memcached, which maintains an
LRU per slab), you can cache reads forever and the old generations will
naturally expire out faster than any "live" cache data.

The QuerySet Cache supports Django versions 1.1 and 1.2.

Behavior
~~~~~~~~

The main goals of Johnny are:

* To cache querysets forever
* To be as simple as possible but still work
* To not increase the conceptual load on the developer

Invalidation
------------

Because queries are cached forever, it's absolutely essential that stale data 
is never accessible in the cache.  Since keys are never actually deleted, but
merely made inaccessible by the progression of a table's generation, 
"invalidation" in this context is the modification of a table's generation key.

The query keys themselves are based on as many uniquely identifying aspects of
a query that we could think of.  This includes the sql itself, the params, the
ordering clause, the database name (1.2 only), and of course the generations of
all of the tables involved.  The following would be two queries, not one::

    MyModel.objects.all().order_by('-created_at')
    MyModel.objects.all().order_by('created_at')

Avoiding the database at all costs was not a goal, so different ordering
clauses on the same dataset are considered different queries.  Since 
invalidation happens at the table level, *any* table having been modified
makes the cached query inaccessible::

    # cached, depends on `publisher` table
    p = Publisher.objects.get(id=5)
    # cached, depends on `book` and `publisher` table
    Book.objects.all().select_related('publisher')
    p.name = "Doubleday"
    # write on `publisher` table, modifies publisher generation
    p.save()
    # the following are cache misses
    Publisher.objects.get(id=5)
    Book.objects.all().select_related('publisher')
    
Because invalidation is greedy in this way, it makes sense to test Johnny
against your site to see if this type of caching is beneficial.

Transactions
------------

Transactions represent an interesting problem to Johnny.  Because the cache
is global, but data written in a transaction (or read from within a transaction)
is potentially local to the process in the transaction, this can lead to 
several scenarios in which queries are cached that do not accurately represent
the contents of the database:

Scenario 1:
***********

* Server1 enters a transaction, changes Table1;  Table1's generation is modified
* Server2 starts a request, read's from Table1, writes to cache using new
  generation key created by Server1
* Server2 commits transaction, Table1 is now modified but pre-modification data
  is cached against the *current* generation key!

Scenario 2:
***********

* Server1 enters a transaction, changes Table1;  Table1's generation is modified
* Server1 reads from modified Table1, writes to cache using new generation key
* Transaction is rolled back;  future requests read cached data that was never
  committed to the database

There are other scenarios possible, but they all involve over-invalidation, and
since this leads to decreased performance but not incorrectness, addressing
these other issues is not a priority.


Usage
~~~~~

To enable the QuerySet Cache, enable the middleware 
``johnny.middleware.QueryCacheMiddleware``.  This middleware uses the `borg
pattern <http://code.activestate.com/recipes/66531/>`_;  to remove the applied
monkey patch, you can call ``johnny.middleware.QueryCacheMiddleware().unpatch()``.

Settings
~~~~~~~~

There is only one additional setting available for the QuerySet Cache:
``DISABLE_QUERYSET_CACHE``, which will prevent the middleware from applying
its patch.

Signals
~~~~~~~

The QuerySet Cache defines two signals:

* ``johnny.cache.signals.qc_hit``, fired after a cache hit
* ``johnny.cache.signals.qc_miss``, fired after a cache miss

The sender of these signals is always the ``QueryCacheBackend`` itself.

.. todo: describe the signals use & functionality

Customization
~~~~~~~~~~~~~

.. todo: details on providing custom KeyGen's, etc.


