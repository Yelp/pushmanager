from contextlib import nested
import mock

from core import db
from core.util import get_servlet_urlspec
from pushmanager.servlets.delayrequest import DelayRequestServlet
import pushmanager.testing as T
import types

class DelayRequestServletTest(T.TestCase, T.ServletTestMixin):

    @T.class_setup_teardown
    def mock_servlet_env(self):
        self.results = []
        with nested(
            mock.patch.dict(db.Settings, T.MockedSettings),
            mock.patch.object(
                DelayRequestServlet,
                "get_current_user",
                return_value="testuser"
            )
        ):
            yield

    def get_handlers(self):
        return [get_servlet_urlspec(DelayRequestServlet)]

    def call_on_db_complete(self, req):
        mocked_self = mock.Mock()
        mocked_self.current_user = 'fake_pushmaster'
        mocked_self.check_db_results = mock.Mock(return_value=None)

        mocked_self.on_db_complete = types.MethodType(DelayRequestServlet.on_db_complete.im_func, mocked_self)

        def first():
            return req

        mreq = mock.Mock()
        mreq.first = first

        mocked_self.on_db_complete('success', [mock.ANY, mock.ANY, mreq])

    @mock.patch('core.mail.MailQueue.enqueue_user_email')
    def test_no_watched_mailqueue_on_db_complete(self, mailq):
        req = {
            'user': 'testuser',
            'watchers': None,
            'repo': 'repo',
            'branch': 'branch',
            'title': 'title',
            'state': 'delayed',
        }
        self.call_on_db_complete(req)

        no_watcher_call_args = mailq.call_args_list[0][0]
        T.assert_equal(['testuser'], no_watcher_call_args[0])
        T.assert_in('Request for testuser', no_watcher_call_args[1])
        T.assert_in('testuser - title', no_watcher_call_args[1])
        T.assert_in('[push] testuser - title', no_watcher_call_args[2])

    @mock.patch('core.mail.MailQueue.enqueue_user_email')
    def test_watched_mailqueue_on_db_complete(self, mailq):
        req = {
            'user': 'testuser',
            'watchers': 'testuser1,testuser2',
            'repo': 'repo',
            'branch': 'branch',
            'title': 'title',
            'state': 'delayed',
        }
        self.call_on_db_complete(req)

        watched_call_args = mailq.call_args_list[0][0]
        T.assert_equal(['testuser', 'testuser1', 'testuser2'], watched_call_args[0])
        T.assert_in('Request for testuser (testuser1,testuser2)', watched_call_args[1])
        T.assert_in('testuser (testuser1,testuser2) - title', watched_call_args[1])
        T.assert_in('[push] testuser (testuser1,testuser2) - title', watched_call_args[2])


if __name__ == '__main__':
    T.run()
