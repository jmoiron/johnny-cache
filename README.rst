Package ``johnny``
==================

``johnny`` is a caching framework for Django applications.

Generational Caching
~~~~~~~~~~~~~~~~~~~~

The fulcrum of johnny-cache is a patch on the Django ORM's sql execution that
adds maintenance code for per-table generational information.  It is designed
specifically for use with the memcached backend, however it should work on 
other supported caches that support infinite timeouts and have an LRU cache
expiry policy.

A key in the cache is maintained per table in the application that contains a
UUID associated with that table.  *Any time* a write is made against that table,
the UUID is changed (cache write).  This allows you to write additional caching
applications that can use these UUIDs as parts of their caching keys to cache
things infinitely in a coherent manner.

Settings
~~~~~~~~

The following settings can be used to disable different caching functionality
for development purposes:

* ``DISABLE_GENERATIONAL_CACHE`` : disables generational cache upkeep.
* ``ENABLE_CACHE_STATS`` : enables cache statistics logging.

Usage
~~~~~

Queryset Caching
----------------

The *Queryset Cache* is the main feature of ``johnny``.  It maintains the
cache generation keys and caches *all* read queries based on the tables they
hit and the statements themselves.  To enable the Queryset Cache, add
``johnny.middleware.QueryCacheMiddleware`` to *the top* of your
MIDDLEWARE_CLASSES setting.

LocalStoreClearMiddleware
-------------------------

The LocalStore cache is a thread-safe dict/object hybrid that lives in 
``johnny.localstore.Cache`` and is cleared out by the LocalStoreClearMiddleware.
This gives a "global" space to put various pieces of information, useful both
as a per-request local cache (to prevent repeated trips to ``memcached``) as
well as a standard place to put information like media registration, etc.
The ``Cache`` object is created automatically, but to have it cleared at the
end of each request add ``johnny.middleware.LocalStoreClearMiddleware`` to
your MIDDLEWARE_CLASSES.

