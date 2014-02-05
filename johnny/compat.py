# coding: utf-8

"""
Tools to ease compatibility across supported versions of Django & Python.
"""

from __future__ import unicode_literals
import django
from django.db import transaction


def is_managed(using=None):
    if django.VERSION[:2] < (1, 6):
        return transaction.is_managed(using=using)
    return False
    # Or maybe we should run the following line?  I'm not sure…
    # return not transaction.get_autocommit(using=using)


def managed(flag=True, using=None):
    if django.VERSION[:2] < (1, 6):
        transaction.managed(flag=flag, using=using)
    # Maybe we should execute the following line otherwise?  I'm not sure…
    # transaction.set_autocommit(autocommit=not flag, using=using)
