from contextlib import nested
import mock

from core import db
from core.util import get_servlet_urlspec
from servlets.livepush import LivePushServlet
import testing as T
import types

class LivePushServletTest(T.TestCase, T.ServletTestMixin):

    @T.class_setup_teardown
    def mock_servlet_env(self):
        self.results = []
        with nested(
            mock.patch.dict(db.Settings, T.MockedSettings),
            mock.patch.object(
                LivePushServlet,
                "get_current_user",
                return_value="testuser"
            )
        ):
            yield

    def get_handlers(self):
        return [get_servlet_urlspec(LivePushServlet)]

    def call_on_db_complete(self):
        mocked_self = mock.Mock()
        mocked_self.current_user = 'fake_pushmaster'
        mocked_self.check_db_results = mock.Mock(return_value=None)

        mocked_self.on_db_complete = types.MethodType(LivePushServlet.on_db_complete.im_func, mocked_self)

        no_watcher_req = {
            'user': 'testuser',
            'watchers': None,
            'repo': 'repo',
            'branch': 'branch',
            'title': 'title',
            'reviewid': 0,
        }
        watched_req = {
            'user': 'testuser',
            'watchers': 'testuser1,testuser2',
            'repo': 'repo',
            'branch': 'branch',
            'title': 'title',
            'reviewid': 0,
        }
        reqs = [no_watcher_req, watched_req]

        mocked_self.on_db_complete('success', [None, None, None, None, reqs])

    @mock.patch('core.mail.MailQueue.enqueue_user_email')
    def test_mailqueue_on_db_complete(self, mailq):
        self.call_on_db_complete()

        no_watcher_call_args = mailq.call_args_list[0][0]
        T.assert_equal(['testuser'], no_watcher_call_args[0])
        T.assert_in('request for testuser', no_watcher_call_args[1])
        T.assert_in('testuser - title', no_watcher_call_args[1])
        T.assert_in('[push] testuser - title', no_watcher_call_args[2])

        watched_call_args = mailq.call_args_list[1][0]
        T.assert_equal(['testuser', 'testuser1', 'testuser2'], watched_call_args[0])
        T.assert_in('request for testuser (testuser1,testuser2)', watched_call_args[1])
        T.assert_in('testuser (testuser1,testuser2) - title', watched_call_args[1])
        T.assert_in('[push] testuser (testuser1,testuser2) - title', watched_call_args[2])


if __name__ == '__main__':
    T.run()
