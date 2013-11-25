#!/usr/bin/env python

import contextlib
import errno
from exceptions import OSError

import mock

import testing as T
from core import pid


class TestPid(T.TestCase):

    @contextlib.contextmanager
    def mock_method(self, method, return_value, side_effect):
        with mock.patch(method) as mocked_method:
            mocked_method.return_value = return_value
            mocked_method.side_effect = side_effect
            yield

    def test_process_is_alive(self):
        with self.mock_method('%s.pid.os.kill' % __name__, None, None):
            assert pid.is_process_alive(1)

    def test_is_process_alive_permission_error(self):
        def side_effect(x,y):
            raise OSError(errno.EPERM, "Access denied")

        with self.mock_method('%s.pid.os.kill' % __name__, None, side_effect):
            assert pid.is_process_alive(1)

    def test_is_process_alive_generic_error(self):
        def side_effect(x,y):
            raise Exception("fake error for testing")

        with self.mock_method('%s.pid.os.kill' % __name__, None, side_effect):
            T.assert_equal(pid.is_process_alive(1), False)

    def test_kill_processes(self):
        with contextlib.nested(
                self.mock_method('%s.pid.os.kill' % __name__, None, None),
                self.mock_method('%s.pid.is_process_alive' % __name__, False, None)
        ):
            # this should run fine, all processes are dead
            pids = [1, 2, 3, 4, 5]
            pid.kill_processes(pids)
            T.assert_equal(pids, [])

    def test_kill_dead_processes(self):
        def side_effect(*args, **kwargs):
            raise OSError(errno.ESRCH, "process is dead already...")

        with contextlib.nested(
                self.mock_method('%s.pid.os.kill' % __name__, False, side_effect),
                self.mock_method('%s.pid.is_process_alive' % __name__, True, None)
        ):
            # this should run fine too, all processes
            # (coincidentally) died just before we try killing
            # them.
            pids = [1, 2, 3, 4, 5]
            pid.kill_processes(pids)
            T.assert_equal(pids, [])

    def test_kill_processes_os_error(self):
        def side_effect(*args, **kwargs):
            raise OSError(errno.EPERM, "access denied")

        with contextlib.nested(
                self.mock_method('%s.pid.os.kill' % __name__, None, side_effect),
                self.mock_method('%s.pid.is_process_alive' % __name__, True, None)
        ):
            # This will fail with access denied, we can kill the
            # process.
            pids = [1, 2, 3, 4, 5]
            T.assert_raises(OSError, pid.kill_processes, pids)
