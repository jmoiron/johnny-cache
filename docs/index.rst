.. Johnny Cache documentation master file, created by
   sphinx-quickstart on Thu Feb 18 22:05:30 2010.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Johnny Cache
============

Johnny Cache is a caching framework for django_ applications.  It works with
the django caching abstraction, but was developed specifically with the use of
memcached_ in mind.  Its main feature is a patch on Django's ORM that
automatically caches all reads in a consistent manner.  It works with Django 
1.1, 1.2, and 1.3.

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
    
    # add johnny's middleware
    MIDDLEWARE_CLASSES = (
        'johnny.middleware.LocalStoreClearMiddleware',
        'johnny.middleware.QueryCacheMiddleware',
        # ... 
    )
    # some johnny settings
    CACHES = {
        'default' : dict(
            BACKEND = 'johnny.backends.memcached.MemcachedCache',
            LOCATION = ['127.0.0.1:11211'],
            JOHNNY_CACHE = True,
        )
    }
    JOHNNY_MIDDLEWARE_KEY_PREFIX='jc_myproj'

*Note*: The above configuration is for Django 1.3, which radically changed
its cache configuration.  To see a full inspection of options for earlier
versions of Django please see the `queryset cache <queryset_cache.html>`_
docs.

The ``MIDDLEWARE_CLASSES`` setting enables two middlewares:  the outer one
clears a thread-local dict-like cache located at ``johnny.cache.local`` at
the end of every request, and should really be the outer most middleware in
your stack.  The second one enables the main feature of Johnny:  the 
`queryset cache <queryset_cache.html>`_.

The ``CACHES`` configuration includes a `custom backend <backends.html>`_,
which allows cache times of "0" to be interpreted as "forever", and marks
the ``default`` cache backend as the one Johnny will use.

Finally, the project's name is worked into the Johnny key prefix so that if
other projects are run using the same cache pool, Johnny won't confuse the
cache for one project with the cache for another.

With these settings, all of your ORM queries are now cached.  You should
read the `queryset cache documentation <queryset_cache.html>`_ closely to
see if you are doing anything that might require manual invalidation.

Johnny does not define any views, urls, or models, so we can skip adding it
to ``INSTALLED_APPS``.

New in this version
~~~~~~~~~~~~~~~~~~~

* Django 1.3 support

The usage for ``johnny.cache.get_backend`` has changed;  it now returns a
QueryCacheBackend instance rather than the appropriate version of the class.
Most uses of this function would have been ``get_backend()()``, which can now
be effectively replaced with ``get_backend()``.

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

