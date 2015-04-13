"""
Johnny provides a number of backends, all of which are subclassed versions of
django builtins that cache "forever" when passed a 0 timeout. These are
essentially the same as mmalone's inspiring ``django-caching`` application's
`cache backend monkey-patch`_.

The way Django interprets cache backend URIs has changed during its history.
Please consult the specific `cache documentation`_ for your version of Django
for the exact usage you should use.

    .. _`cache backend monkey-patch`: http://github.com/mmalone/django-caching/blob/master/app/cache.py
    .. _`cache documentation`: http://docs.djangoproject.com/en/dev/topics/cache

Example usage::

    CACHES = {
        'default' : {
            'BACKEND': 'johnny.backends.memcached.PyLibMCCache',
            'LOCATION': '...',
        }
    }

**Important Note**:  The ``locmem`` and ``filebased`` caches are NOT
recommended for setups in which there is more than one server using Johnny;
invalidation will break with potentially disasterous results if the cache
Johnny uses is not shared amongst all machines writing to the database.
"""

__all__ = ['memcached', 'locmem', 'filebased']
