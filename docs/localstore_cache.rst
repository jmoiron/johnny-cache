.. localstore cache document

The LocalStore Cache
====================

It is a thread-local dict-like object that is cleared at the end of each 
request by an associated middleware.  This can be useful for global data that 
just be kept, referred to, or even modified throughout the lifetime of a 
request, like messaging, media registration, or cached datasets.

By default, the LocalStore Cache *just is*.  It is an instantiated object
of the ``johnny.localstore.LocalStore`` class located in ``johnny.cache.local``.
The use of the class comes from the middleware that clears it at the end
of each request.  Being a module-level object, it is a singleton.

