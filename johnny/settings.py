from django.conf import settings

DISABLE_QUERYSET_CACHE = getattr(settings, 'DISABLE_QUERYSET_CACHE', False)

BLACKLIST = getattr(settings, 'MAN_IN_BLACKLIST',
            getattr(settings, 'JOHNNY_TABLE_BLACKLIST', []))
BLACKLIST = set(BLACKLIST)

MIDDLEWARE_KEY_PREFIX = getattr(settings, 'JOHNNY_MIDDLEWARE_KEY_PREFIX', 'jc')

MIDDLEWARE_SECONDS = getattr(settings, 'JOHNNY_MIDDLEWARE_SECONDS', 0)

CACHE_BACKEND = getattr(settings, 'JOHNNY_CACHE_BACKEND', 
                getattr(settings, 'CACHE_BACKEND', None))
