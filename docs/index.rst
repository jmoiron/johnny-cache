.. Johnny Cache documentation master file, created by
   sphinx-quickstart on Thu Feb 18 22:05:30 2010.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Johnny Cache
============

Johnny Cache is a caching framework for django_ applications.  It works with
the django caching abstraction, but was developed specifically with the use of
memcached_ in mind.

You can fork johnny-cache `from its hg repository 
<http://dev.jmoiron.net/hg/johnny-cache>`_.

.. _django: http://djangoproject.com
.. _memcached: http://memcached.org

Introduction
~~~~~~~~~~~~

Johnny Cache is a collection of various tools and applications to assist with
caching for web applications.  The main feature is a patch on the Django ORM's
sql execution that caches *every* database read forever but properly
invalidates the cache on any write to the database.

In Depth Documentation
~~~~~~~~~~~~~~~~~~~~~~

.. toctree::
   :maxdepth: 1

   queryset_cache
   localstore_cache
   backends


Feature Overview
================

QuerySet Caching
~~~~~~~~~~~~~~~~

QuerySet caching is the automatic caching of all database reads.  Conceptually, 
it works very similar to the built-in write-invalidate queryset caching that 
is present in your RDBMS.  

When a read (``SELECT``) is made from one or more tables, that read is cached. 
When a write (``INSERT``, ``UPDATE``, etc) is made against that table, the 
read cache built up for that table is invalidated.  This type of caching can be 
very beneficial when an app is very read heavy and write light, or when writing 
is confined to a few tables, but generaly helps pull lots of read traffic off
of the database servers.

The QuerySet Cache supports Django versions 1.1 and 1.2.

LocalStore Cache
~~~~~~~~~~~~~~~~

Johnny provides a cache called the *LocalStore* Cache.  It is a
thread-local dict-like object that is cleared at the end of each request by
an associated middleware.  This can be useful for global data that must be
kept, referred to, or even modified throughout the lifetime of a request,
like messaging, media registration, or cached datasets.

.. Indices and tables
.. ==================

.. * :ref:`modindex`
.. * :ref:`genindex`
.. * :ref:`search`

