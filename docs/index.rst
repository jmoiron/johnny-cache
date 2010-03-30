.. Johnny Cache documentation master file, created by
   sphinx-quickstart on Thu Feb 18 22:05:30 2010.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Johnny Cache
============

Johnny Cache is a caching framework for django_ applications.  It works with
the django caching abstraction, but was developed specifically with the use of
memcached_ in mind.  Its main feature is a patch on Django's ORM that
automatically caches all reads in a consistent manner.

.. highlight:: sh

You can install johnny with pip::

    pip install johnny-cache


You can fork johnny-cache `from its hg repository 
<http://bitbucket.org/jmoiron/johnny-cache>`_::

    hg clone http://bitbucket.org/jmoiron/johnny-cache


Please use `bitbucket's issue tracker
<http://bitbucket.org/jmoiron/johnny-cache/issues/>`_ to report bugs. Contact 
the authors at `@jmoiron`_ and `@finder83`_.

.. _django: http://djangoproject.com
.. _memcached: http://memcached.org
.. _@jmoiron: http://twitter.com/jmoiron
.. _@finder83: http://twitter.com/finder83

Usage
=====

.. highlight:: python

A typical ``settings.py`` file configured for ``johnny-cache``::
    
    # add johnny to installed apps
    INSTALLED_APPS = ( 
        # ...
        'johnny',
    )
    # add johnny's middleware
    MIDDLEWARE_CLASSES = (
        'johnny.middleware.LocalStoreClearMiddleware',
        'johnny.middleware.QueryCacheMiddleware',
        # ... 
    )
    # some johnny settings
    CACHE_BACKEND = 'johnny.backends.memcached://...'
    JOHNNY_MIDDLEWARE_KEY_PREFIX='jc_myproj'

Django doesn't *actually* require libraries to be 'installed', and since
Johnny doesn't define any views, urls, or models, the first step isn't a
requirement, but we like to make it clear what we're using and where on the
``PYTHONPATH`` it might be.

The ``MIDDLEWARE_CLASSES`` setting enables two middlewares:  the outer one
clears a thread-local dict-like cache located at ``johnny.cache.local`` at
the end of every request, and should really be the outer most middleware in
your stack.  The second one enables the main feature of Johnny:  the 
`queryset cache <queryset_cache.html>`_.

The `custom backend setting <backends.html>`_ enables a thin wrapper around
Django's ``memcached`` (or ``locmem``) cache class that allows cache times
of "0", which memcached interprets as "forever" and locmem is patched to 
see as forever.

Finally, the project's name is worked into the Johnny key prefix so that if
other projects are run using the same cache pool, Johnny won't confuse the
cache for one project with the cache for another.

With these settings, all of your ORM queries are now cached.  You should
read the `queryset cache documentation <queryset_cache.html>`_ closely to
see if you are doing anything that might require manual invalidation.

In Depth Documentation
~~~~~~~~~~~~~~~~~~~~~~

.. toctree::
   :maxdepth: 1

   queryset_cache
   localstore_cache
   backends

.. Feature Overview
.. ================

.. QuerySet Caching
.. ~~~~~~~~~~~~~~~~

.. QuerySet caching is the automatic caching of all database reads.  Conceptually, 
.. it works very similar to the built-in write-invalidate queryset caching that 
.. is present in your RDBMS.  

.. When a read (``SELECT``) is made from one or more tables, that read is cached. 
.. When a write (``INSERT``, ``UPDATE``, etc) is made against that table, the 
.. read cache built up for that table is invalidated.  This type of caching can be 
.. very beneficial when an app is very read heavy and write light, or when writing 
.. is confined to a few tables, but generaly helps pull lots of read traffic off
.. of the database servers.

.. The QuerySet Cache supports Django versions 1.1 and 1.2.

.. LocalStore Cache
.. ~~~~~~~~~~~~~~~~

.. Johnny provides a cache called the *LocalStore* Cache.  It is a
.. thread-local dict-like object that is cleared at the end of each request by
.. an associated middleware.  This can be useful for global data that must be
.. kept, referred to, or even modified throughout the lifetime of a request,
.. like messaging, media registration, or cached datasets.

.. Indices and tables
.. ==================

.. * :ref:`modindex`
.. * :ref:`genindex`
.. * :ref:`search`

