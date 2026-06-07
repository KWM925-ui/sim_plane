def is_aiogrpc_current_thread_join_error(exc):
    return isinstance(exc, RuntimeError) and str(exc) == "cannot join current thread"


def guard_aiogrpc_wrapped_iterator_del(original_del):
    def guarded_del(wrapped_iterator):
        try:
            return original_del(wrapped_iterator)
        except RuntimeError as exc:
            if is_aiogrpc_current_thread_join_error(exc):
                return None
            raise

    return guarded_del


def install_aiogrpc_wrapped_iterator_del_guard():
    try:
        from aiogrpc import utils
    except Exception:
        return False

    wrapped_iterator = getattr(utils, "WrappedIterator", None)
    if wrapped_iterator is None:
        return False
    if getattr(wrapped_iterator, "_sim_plane_del_guard_installed", False):
        return False

    original_del = getattr(wrapped_iterator, "__del__", None)
    if not callable(original_del):
        return False

    wrapped_iterator._sim_plane_original_del = original_del
    wrapped_iterator.__del__ = guard_aiogrpc_wrapped_iterator_del(original_del)
    wrapped_iterator._sim_plane_del_guard_installed = True
    return True
