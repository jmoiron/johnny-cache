.. localstore cache document

.. module:: johnny.localstore

The LocalStore Cache
====================

It is a thread-local dict-like object that is cleared at the end of each 
request by an associated middleware.  This can be useful for global data that 
just be kept, referred to, or even modified throughout the lifetime of a 
request, like messaging, media registration, or cached datasets.

By default, the LocalStore cache is an instantiated copy of
the ``johnny.localstore.LocalStore`` class located in ``johnny.cache.local``.
The usefulness of the class comes from the middleware that clears it at the end
of each request.  Being a module-level object, it is a singleton.

Johnny relies on ``johnny.cache.local`` for its transaction and savepoint
support, so it is a good idea to enable the middleware to clear it per request
as not doing so can gradually leak memory as this object has no built-in
eviction.

.. autoclass:: johnny.localstore.LocalStore

