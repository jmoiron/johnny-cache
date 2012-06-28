#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Extra johnny utilities."""

from johnny.cache import get_backend, local, patch, unpatch
from johnny.decorators import wraps, available_attrs


__all__ = ["celery_enable_all", "celery_task_wrapper", "johnny_task_wrapper"]


def prerun_handler(*args, **kwargs):
    """Celery pre-run handler.  Enables johnny-cache."""
    patch()

def postrun_handler(*args, **kwargs):
    """Celery postrun handler.  Unpatches and clears the localstore."""
    unpatch()
    local.clear()

def celery_enable_all():
    """Enable johnny-cache in all celery tasks, clearing the local-store
    after each task."""
    from celery.signals import task_prerun, task_postrun, task_failure
    task_prerun.connect(prerun_handler)
    task_postrun.connect(postrun_handler)
    # Also have to cleanup on failure.
    task_failure.connect(postrun_handler)

def celery_task_wrapper(f):
    """
    Provides a task wrapper for celery that sets up cache and ensures
    that the local store is cleared after completion
    """
    from celery.utils import fun_takes_kwargs

    @wraps(f, assigned=available_attrs(f))
    def newf(*args, **kwargs):
        backend = get_backend()
        was_patched = backend._patched
        get_backend().patch()
        # since this function takes all keyword arguments,
        # we will pass only the ones the function below accepts,
        # just as celery does
        supported_keys = fun_takes_kwargs(f, kwargs)
        new_kwargs = dict((key, val) for key, val in kwargs.items()
                                if key in supported_keys)

        try:
            ret = f(*args, **new_kwargs)
        finally:
            local.clear()
        if not was_patched:
            get_backend().unpatch()
        return ret
    return newf

# backwards compatible alias
johnny_task_wrapper = celery_task_wrapper

