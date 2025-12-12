import time
import globals_cache as gc


def is_cache_expired():
    if gc.loaded_timestamp is None:
        return True
    return (time.time() - gc.loaded_timestamp) > gc.CACHE_TTL_SECONDS