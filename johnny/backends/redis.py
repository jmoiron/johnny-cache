"""
Redis cache classes that forcebly limits the timeout of the redis
cache backend to 30 days to make sure the cache doesn't fill up
when johnny always caches queries. Redis doesn't have an automatic
cache invalidation other than timeouts.

This module depends on the ``django-redis-cache`` app from PyPI.
"""

from redis_cache import cache as redis


class RedisCache(redis.RedisCache):
    def set(self, key, value, timeout=None, *args, **kwargs):
        if timeout == 0:
            timeout = 2591999
        return super(RedisCache, self).set(key, value, timeout,
                                           *args, **kwargs)
