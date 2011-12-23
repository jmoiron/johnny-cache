"""
Infinite caching memcached class.  Caches forever when passed a timeout
of 0.  For Django >= 1.3, this module also provides ``MemcachedCache`` and
``PyLibMCCache``, which use the backends of their respective analogs in
django's default backend modules.
"""

import django
from django.core.cache.backends import memcached


class CacheClass(memcached.CacheClass):
    """
    By checking ``timeout is None`` rather than ``not timeout``, this
    cache class allows for non-expiring cache writes on certain backends,
    notably memcached.
    """
    def _get_memcache_timeout(self, timeout=None):
        if timeout == 0:
            return 0  # 2591999
        return super(CacheClass, self)._get_memcache_timeout(timeout)

if django.VERSION[:2] > (1, 2):

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
