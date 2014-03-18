# Django settings for proj project.

import os
import warnings
import django

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = ()

MANAGERS = ADMINS

db_engine = os.environ.get('DB_ENGINE', 'sqlite3')
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.' + db_engine,
        'NAME': 'johnny_db',
        'TEST_NAME': 'test_johnny_db',
    },
    'second': {
        'ENGINE': 'django.db.backends.' + db_engine,
        'NAME': 'johnny2_db',
        'TEST_NAME': 'test_johnny2_db',
    },
}
if db_engine == 'postgresql_psycopg2':
    DATABASES['default']['OPTIONS'] = {'autocommit': True}
    DATABASES['second']['OPTIONS'] = {'autocommit': True}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

cache_backend = os.environ.get('CACHE_BACKEND', 'memcached')
if cache_backend == 'memcached':
    CACHES = {
        'default': {
            'BACKEND': 'johnny.backends.memcached.MemcachedCache',
            'LOCATION': ['localhost:11211'],
            'JOHNNY_CACHE': True,
        }
    }
elif cache_backend == 'redis':
    CACHES = {
        'default': {
            'BACKEND': 'johnny.backends.redis.RedisCache',
            'LOCATION': 'localhost:6379:0',
            'JOHNNY_CACHE': True,
        }
    }
elif cache_backend == 'locmem':
    CACHES = {
        'default': {
            'BACKEND': 'johnny.backends.locmem.LocMemCache',
        }
    }
    warnings.warn('Some tests may fail with the locmem cache backend!')
elif cache_backend == 'filebased':
    CACHES = {
        'default': {
            'BACKEND': 'johnny.backends.filebased.FileBasedCache',
            'LOCATION': '_cache',
        }
    }
    warnings.warn('Some tests may fail with the file-based cache backend!')
else:
    raise ValueError('The CACHE_BACKEND environment variable is invalid.')


# Make this unique, and don't share it with anybody.
SECRET_KEY = '_vpn1a^j(6&+3qip2me4f#&8#m#*#icc!%=x=)rha4k=!4m8s4'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
#    'django.template.loaders.app_directories.Loader',
#    'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

ROOT_URLCONF = 'proj.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    #'django.contrib.auth',
    #'django.contrib.sessions',
    #'django.contrib.sites',
    'johnny',
)

try:
    from local_settings import *
except ImportError:
    pass

# set up a multi-db router if there are multiple databases set
lcls = locals()
if 'DATABASES' in lcls and len(lcls['DATABASES']) > 1:
    DATABASE_ROUTERS = ['routers.MultiSyncedRouter']

TEST_RUNNER = 'django.test.simple.DjangoTestSuiteRunner'
