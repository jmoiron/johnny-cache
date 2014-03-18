.. image:: https://travis-ci.org/jmoiron/johnny-cache.png
  :target: https://travis-ci.org/jmoiron/johnny-cache

.. image:: https://coveralls.io/repos/jmoiron/johnny-cache/badge.png
  :target: https://coveralls.io/r/jmoiron/johnny-cache


Johnny Cache is a caching framework for django_ applications.  It works with
the django caching abstraction, but was developed specifically with the use of
memcached_ in mind.  Its main feature is a patch on Django's ORM that
automatically caches all reads in a consistent manner.

You can install johnny with pip::

    pip install johnny-cache

You can fork johnny-cache `from its git repository
<http://github.com/jmoiron/johnny-cache>`_::
    
    git clone http://github.com/jmoiron/johnny-cache.git

Or if you prefer mercurial, `from its hg mirror 
<http://bitbucket.org/jmoiron/johnny-cache>`_::

    hg clone http://bitbucket.org/jmoiron/johnny-cache


Please read `The full documentation to Johnny Cache
<http://packages.python.org/johnny-cache/>`_ before using it.

.. _django: http://djangoproject.com
.. _memcached: http://memcached.org
