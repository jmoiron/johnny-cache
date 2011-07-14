try:
    from celery.utils import fun_takes_kwargs
except:
    fun_takes_kwargs = None
try:
    from functools import wraps
except:
    from django.utils.functional import wraps

from johnny.cache import get_backend, local

def johnny_task_wrapper(f):
    """
    Provides a task wrapper for celery that sets up cache and ensures
    that the local store is cleared after completion
    """
    if fun_takes_kwargs is None:
        return f
    @wraps(f)
    def newf(*args, **kwargs):
        backend = get_backend()
        was_patched = backend._patched
        get_backend().patch()
        #since this function takes all keyword arguments,
        #we will pass only the ones the function below accepts, just as celery does
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
