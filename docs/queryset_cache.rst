.. queryset cache main documentation, including options, enabling/disabling,
   using with raw sql and cursors, signals, etc

.. module:: johnny.cache

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

.. autoclass:: johnny.cache.QueryCacheBackend

.. autofunction:: johnny.cache.get_backend

The main goals of the QuerySet Cache are:

* To cache querysets forever
* To be as simple as possible but still work
* To not increase the conceptual load on the developer

Invalidation
~~~~~~~~~~~~

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

Transactions represent an interesting problem to caches like Johnny.  Because
the generation keys are invalidated on write, and a transaction commit does not
go down the same code path as our invalidation, there are a number of scenarios
involving transactions that could cause problems.

The most obvious one is write and a read within a transaction that gets rolled
back.  The write invalidates the cache key, the read puts new data into the
cache, but that new data never actually sees the light of day in the database.
There are numerous other concurrency related issues with invalidating keys
within transactions regardless of whether or not a rollback is performed,
because the generational key change is in memcached and thus not protected by
the transaction itself.

Because of this, when you enable Johnny, the ``django.db.transaction`` module
is patched in various places to place new hooks around transaction rollback
and committal.  When you are in what django terms a "managed transaction", ie
a transaction that *you* are managing manually, Johnny automatically writes
any cache keys to the `LocalStore <'localstore_cache.html'>`_ instead.  
On commit, these keys are pushed to the global cache;  on rollback, they are
discarded.

Savepoints
----------

Preliminary savepoint support is included in version 0.1.  More testing is
needed (and welcomed).  Currently, the only django backend that has support 
for Savepoints is the PostgreSQL backend (MySQL's InnoDB engine 
`supports savepoints <http://dev.mysql.com/doc/refman/5.0/en/savepoint.html>`_, 
but its backend doesn't).  If you use savepoints, please see the 
:ref:`manual-invalidation` section.

Usage
~~~~~

To enable the QuerySet Cache, enable the middleware 
``johnny.middleware.QueryCacheMiddleware``.  This middleware uses the `borg
pattern <http://code.activestate.com/recipes/66531/>`_;  to remove the applied
monkey patch, you can call ``johnny.middleware.QueryCacheMiddleware().unpatch()``,
but the middleware will attempt to install itself again unless you also
set ``settings.DISABLE_QUERYSET_CACHE`` to ``True``.

.. _manual-invalidation:

Manual Invalidation
-------------------

To manually invalidate a table or a model, use ``johnny.cache.invalidate``:

.. autofunction:: johnny.cache.invalidate


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

Customization
~~~~~~~~~~~~~

There are many aspects of the behavior of the QuerySet Cache that are pluggable,
but no easy settings-style hooks are yet provided for them.  More ability to
control the way Johnny functions is planned for future releases.

.. todo: details on providing custom KeyGen's, etc.

