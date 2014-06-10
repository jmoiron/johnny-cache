from warnings import warn

from django.conf import settings
from django.core.cache import get_cache, cache

DISABLE_QUERYSET_CACHE = getattr(settings, 'DISABLE_QUERYSET_CACHE', False)

DEFAULT_BLACKLIST = ['south_migrationhistory']

BLACKLIST = list(getattr(settings, 'MAN_IN_BLACKLIST',
            getattr(settings, 'JOHNNY_TABLE_BLACKLIST', []))) + DEFAULT_BLACKLIST
BLACKLIST = set(BLACKLIST)

WHITELIST = set(getattr(settings, 'JOHNNY_TABLE_WHITELIST', []))

DB_CACHE_KEYS = dict((name, db.get('JOHNNY_CACHE_KEY', name))
                 for name, db in settings.DATABASES.items())

MIDDLEWARE_KEY_PREFIX = getattr(settings, 'JOHNNY_MIDDLEWARE_KEY_PREFIX', 'jc')

MIDDLEWARE_SECONDS = getattr(settings, 'JOHNNY_MIDDLEWARE_SECONDS', 0)

CACHE_BACKEND = getattr(settings, 'JOHNNY_CACHE_BACKEND',
                getattr(settings, 'CACHE_BACKEND', None))

CACHES = getattr(settings, 'CACHES', {})


def _get_backend():
    """
    Returns the actual django cache object johnny is configured to use.
    This relies on the settings only;  the actual active cache can
    theoretically be changed at runtime.
    """
    enabled = [n for n, c in sorted(CACHES.items())
               if c.get('JOHNNY_CACHE', False)]
    if len(enabled) > 1:
        warn("Multiple caches configured for johnny-cache; using %s." %
             enabled[0])
    if enabled:
        return get_cache(enabled[0])
    if CACHE_BACKEND:
        backend = get_cache(CACHE_BACKEND)
        if backend not in CACHES:
            from django.core import signals
            # Some caches -- python-memcached in particular -- need to do a
            # cleanup at the end of a request cycle. If the cache provides a
            # close() method, wire it up here.
            if hasattr(backend, 'close'):
                signals.request_finished.connect(backend.close)
        return backend
    return cache
