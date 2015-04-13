# coding: utf-8

"""
Tools to ease compatibility across supported versions of Django & Python.
"""

from __future__ import unicode_literals
from django.db.models.sql import compiler


try:
    from queue import Queue
except ImportError:  # Python < 3.0
    from Queue import Queue

import django
from django.db import transaction

try:
    from django.utils.encoding import force_bytes, force_text
    from django.utils.six import string_types, text_type
except ImportError:  # Django < 1.4.2
    force_bytes = str
    force_text = unicode
    string_types = (str, unicode)
    text_type = unicode


__all__ = (
    'Queue', 'force_bytes', 'force_text', 'string_types', 'text_type',
    'empty_iter', 'is_managed', 'managed',
)


def empty_iter():
    if django.VERSION[:2] >= (1, 5):
        return iter([])
    return compiler.empty_iter()


def is_managed(using=None):
    if django.VERSION[:2] < (1, 6):
        return transaction.is_managed(using=using)
    elif django.VERSION[:2] >= (1, 6):
        # See https://code.djangoproject.com/ticket/21004
        return not transaction.get_autocommit(using=using)
    return False


def managed(flag=True, using=None):
    if django.VERSION[:2] < (1, 6):
        transaction.managed(flag=flag, using=using)
    elif django.VERSION[:2] >= (1, 6):
        transaction.set_autocommit(not flag, using=using)
