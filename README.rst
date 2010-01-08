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

* ``JOHNNY_CACHE_EXTENSIONS`` : a list of app strings that hook into the
  generational cache.  The default is (``johnny.apps.QuerySetCache``,).

* ``DISABLE_GENERATIONAL_CACHE`` : disables generational cache upkeep.

* ``ENABLE_CACHE_STATS`` : enables cache statistics logging.

Usage
~~~~~

Generational Cache Upkeep
-------------------------

This is the foundation of ``johnny`` and must be enabled for any sub-app
that requires it.  To enable the generational cache upkeep, install the
``johnny.middleware.GenerationalCacheMiddleware``.  You can leave this
middleware installed but disable its activities by using the
``DISABLE_GENERATIONAL_CACHE`` setting.

Queryset Cache
--------------

The *Queryset Cache* is a generational 2-tiered caching system implemented as a
sub-app of the generational cache.  The generational cache middleware applies a
monkey-patch to the Django ORM, but also supplies hooks for other caching apps.
To enable the Queryset Cache, add ``johnny.apps.QuerySetCache`` to the 
``JOHNNY_CACHE_EXTENSIONS`` setting.

