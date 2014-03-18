"""
Infinite caching memcached classes.  Caches forever when passed a timeout
of 0.
"""

import logging

from django.core.cache.backends import memcached


class MemcachedCache(memcached.MemcachedCache):
    """
    Infinitely Caching version of django's MemcachedCache backend.
    """
    def _get_memcache_timeout(self, timeout=None):
        if timeout == 0:
            return 0  # 2591999
        return super(MemcachedCache, self)._get_memcache_timeout(timeout)


class PyLibMCCache(memcached.PyLibMCCache):
    """
    PyLibMCCache version that interprets 0 to mean, roughly, 30 days.
    This is because `pylibmc interprets 0 to mean literally zero seconds
    <http://sendapatch.se/projects/pylibmc/misc.html#differences-from-python-memcached>`_
    rather than "infinity" as memcached itself does.  The maximum timeout
    memcached allows before treating the timeout as a timestamp is just
    under 30 days.
    """
    def _get_memcache_timeout(self, timeout=None):
        # pylibmc doesn't like our definition of 0
        if timeout == 0:
            return 2591999
        return super(PyLibMCCache, self)._get_memcache_timeout(timeout)


class FailSilentlyMemcachedCache(MemcachedCache):
    """
    It may happen that we're trying to cache something bigger that the
    max allowed per key on memcached. Instead of failing with a ValueError
    exception, this backend allows to ignore that, even if it means
    not to store the cached value, but at least the application will
    keep working.
    """
    def set(self, *args, **kwargs):
        try:
            super(FailSilentlyMemcachedCache, self).set(*args, **kwargs)
        except ValueError:
            logging.warning("Couldn't set the key for the cache")
