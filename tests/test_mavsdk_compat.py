import unittest

from sim_plane.adapters.mavsdk_compat import (
    guard_aiogrpc_wrapped_iterator_del,
    install_aiogrpc_wrapped_iterator_del_guard,
    is_aiogrpc_current_thread_join_error,
)


class MAVSDKCompatTest(unittest.TestCase):
    def test_detects_only_aiogrpc_current_thread_join_error(self):
        self.assertTrue(is_aiogrpc_current_thread_join_error(RuntimeError("cannot join current thread")))
        self.assertFalse(is_aiogrpc_current_thread_join_error(RuntimeError("other cleanup failure")))
        self.assertFalse(is_aiogrpc_current_thread_join_error(ValueError("cannot join current thread")))

    def test_guard_suppresses_only_known_join_noise(self):
        def noisy_del(_):
            raise RuntimeError("cannot join current thread")

        guarded = guard_aiogrpc_wrapped_iterator_del(noisy_del)
        self.assertIsNone(guarded(object()))

        def broken_del(_):
            raise RuntimeError("other cleanup failure")

        guarded = guard_aiogrpc_wrapped_iterator_del(broken_del)
        with self.assertRaises(RuntimeError):
            guarded(object())

    def test_install_guard_is_idempotent_when_aiogrpc_is_available(self):
        first = install_aiogrpc_wrapped_iterator_del_guard()
        second = install_aiogrpc_wrapped_iterator_del_guard()
        self.assertFalse(first and second)


if __name__ == "__main__":
    unittest.main()
