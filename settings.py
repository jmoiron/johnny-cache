# Django settings for proj project.

import django

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = ()

MANAGERS = ADMINS

if django.VERSION[:2] < (1, 3):
    DATABASE_ENGINE = 'sqlite3'     # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
    DATABASE_NAME = 'johnny-db.db' # Or path to database file if using sqlite3.
    DATABASE_USER = ''              # Not used with sqlite3.
    DATABASE_PASSWORD = ''          # Not used with sqlite3.
    DATABASE_HOST = ''              # Set to empty string for localhost. Not used with sqlite3.
    DATABASE_PORT = ''              # Set to empty string for default. Not used with sqlite3.
else:
    DATABASES = {
        'default' : {
            'ENGINE' : 'django.db.backends.sqlite3',
            'NAME' : 'johnny-db.db',
        }
    }

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

if django.VERSION[:2] < (1, 3):
    #CACHE_BACKEND="johnny.backends.locmem://"
    CACHE_BACKEND="johnny.backends.memcached://localhost:11211/"
    #CACHE_BACKEND="johnny.backends.filebased:///tmp/johnny_cache.cc"
else:
    #CACHES = { 'default' : { 'BACKEND': 'johnny.backends.locmem.LocMemCache' }}
    CACHES = {
        'default' : {
            'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
            #'BACKEND': 'johnny.backends.memcached.MemcachedCache',
            'LOCATION': ['localhost:11211'],
            'JOHNNY_CACHE': True,
        }
    }


# Make this unique, and don't share it with anybody.
SECRET_KEY = '_vpn1a^j(6&+3qip2me4f#&8#m#*#icc!%=x=)rha4k=!4m8s4'

# List of callables that know how to import templates from various sources.
if django.VERSION[:2] < (1, 3):
    TEMPLATE_LOADERS = (
        'django.template.loaders.filesystem.load_template_source',
    #    'django.template.loaders.app_directories.load_template_source',
    #    'django.template.loaders.eggs.load_template_source',
    )
else:
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
