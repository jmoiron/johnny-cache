Johnny Cache is a caching framework for django_ applications.  It works with
the django caching abstraction, but was developed specifically with the use of
memcached_ in mind.  Its main feature is a patch on Django's ORM that
automatically caches all reads in a consistent manner.

You can install johnny with pip::

    pip install johnny-cache


You can fork johnny-cache `from its hg repository 
<http://bitbucket.org/jmoiron/johnny-cache>`_::

    hg clone http://bitbucket.org/jmoiron/johnny-cache


Please read `The full documentation to Johnny Cache
<http://packages.python.org/johnny-cache/>`_ before using it as there are a few
edge cases where automatic invalidation was not possible.

.. _django: http://djangoproject.com
.. _memcached: http://memcached.org
