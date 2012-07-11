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
1.1 thru 1.4 and python 2.4 thru 2.7.

.. highlight:: sh

You can install johnny with pip::

    pip install johnny-cache

You can fork johnny-cache `from its git repository`_::

    git clone https://github.com/jmoiron/johnny-cache.git

or, if you prefer, from its `hg mirror`_::

    hg clone http://bitbucket.org/jmoiron/johnny-cache

Please use `github's issue tracker`_ to report bugs.  Contact the authors at
`@jmoiron`_ and `@finder83`_.

.. _django: http://djangoproject.com
.. _memcached: http://memcached.org
.. _@jmoiron: http://twitter.com/jmoiron
.. _@finder83: http://twitter.com/finder83
.. _github's issue tracker: https://github.com/jmoiron/johnny-cache/issues
.. _from its git repository: https://github.com/jmoiron/johnny-cache
.. _hg mirror: http://bitbucket.org/jmoiron/johnny-cache


Usage
=====

.. highlight:: python

A typical ``settings.py`` file for Django 1.3 or 1.4 configured for
``johnny-cache``::
    
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

For a full inspection of options for earlier versions of Django please see 
the `queryset cache <queryset_cache.html>`_ docs.

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

*Note*: Since Johnny is enabled by the inclusion of middleware, it will not
be enabled by default in scripts, management commands, asynchronous workers,
or the django shell.  See `the queryset cache documentation
<queryset_cache.html#using-with-scripts-management-commands-asynchronous-workers-and-the-shell>`_
for instructions on how to enable it in these cases.


New in this version
~~~~~~~~~~~~~~~~~~~

* Django 1.4 support
* Redis backend (requires ``django-redis-cache``)
* Master/Slave support
* Cache whitelist
* New celery task utilities

Version Numbering
~~~~~~~~~~~~~~~~~

Because Johnny tracks Django's release schedule with its own releases, and is
itself a mature project, the version number has been bumped from 0.3 to 1.4 to
coincide with the highest version of Django with support.  In the future,
Johnny's version will track the major and minor version numbers of Django, but
will have independent dot releases for bugfixes, maintenance, and backwards
compatible feature enhancements.

Deprecation Policy
~~~~~~~~~~~~~~~~~~

As of the release of Django 1.4, Django 1.1 and 1.2 are now officially
unsupported projects.  In addition, in an effort to clean up code in preparation
for eventual Python 3.3 support, Django 1.4 drops support for Python 2.4 and 
Django 1.5 will drop support for Python 2.5.

Johnny 1.4 will maintain support for Django 1.1+ and Python 2.4 thru 2.7, as
previous releases have had no official deprecation policies.  Future versions
will:

 * Adopt Django's Python version support & deprecation policy (including py3k
   adoption)
 * Support the 3 most recent versions of Django

If Django development goals are met, this means that Johnny 1.5 will support
Django 1.3-1.5 and Python 2.6+, with experimental Python 3.3 support.  This
also means that, while future versions of Johnny will be compatible with older
versions of Django, they might not be compatible with all of the supported
versions of *python* for these old versions.


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

