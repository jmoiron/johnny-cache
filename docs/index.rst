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

New in this version
~~~~~~~~~~~~~~~~~~~

* many, many bugfixes
* fixes for invalidation on queries that contain subselects in WHERE clauses
* addition of `TransactionCommittingMiddleware <queryset_cache.html#using-with-transactionmiddleware>`_
* python 2.4 support

Future Django 1.3 Support
~~~~~~~~~~~~~~~~~~~~~~~~~

``johnny-cache`` is currently *not* compatible with Django 1.3b.  Version 0.2.1
provides cache classes in the vein of the new cache classes for what will be
Django 1.3, but johnny's transaction support is not functional in 1.3 yet.

After 1.3 final is released, johnny 0.3 will be released, which will fully
support 1.1-1.3.  If you need to run with 1.3 or django-trunk in the meantime,
be mindful that Johnny can potentially cache (forever) reads that are done
within a failing transaction, and please use it only if you are sure that this
will not impact your application.

In Depth Documentation
~~~~~~~~~~~~~~~~~~~~~~

.. toctree::
   :maxdepth: 1

   queryset_cache
   localstore_cache
   backends

.. * :ref:`modindex`
.. * :ref:`genindex`
.. * :ref:`search`

