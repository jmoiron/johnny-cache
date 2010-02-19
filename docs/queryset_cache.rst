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

Usage
=====

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
=============

.. todo: details on providing custom KeyGen's, etc.


