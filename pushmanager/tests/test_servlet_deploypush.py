from contextlib import nested
import mock

from core import db
from core.util import get_servlet_urlspec
from servlets.deploypush import DeployPushServlet
import testing as T
import types

class DeployPushServletTest(T.TestCase, T.ServletTestMixin):

    @T.class_setup_teardown
    def mock_servlet_env(self):
        self.results = []
        with nested(
            mock.patch.dict(db.Settings, T.MockedSettings),
            mock.patch.object(
                DeployPushServlet,
                "get_current_user",
                return_value="testuser"
            )
        ):
            yield

    def get_handlers(self):
        return [get_servlet_urlspec(DeployPushServlet)]

    def call_on_db_complete(self):
        mocked_self = mock.Mock()
        mocked_self.current_user = 'fake_pushmaster'
        mocked_self.pushid = 0
        mocked_self.check_db_results = mock.Mock(return_value=None)

        mocked_self.on_db_complete = types.MethodType(DeployPushServlet.on_db_complete.im_func, mocked_self)

        no_watcher_req = {
            'user': 'testuser',
            'watchers': None,
            'repo': 'repo',
            'branch': 'branch',
            'title': 'title',
        }
        watched_req = {
            'user': 'testuser',
            'watchers': 'testuser1,testuser2',
            'repo': 'repo',
            'branch': 'branch',
            'title': 'title',
        }
        reqs = [no_watcher_req, watched_req]

        def fetchone():
            return {'extra_pings': None, 'stageenv': None}

        res = mock.Mock()
        res.fetchone = fetchone

        mocked_self.on_db_complete('success', [None, reqs, res])

    @mock.patch('core.xmppclient.XMPPQueue.enqueue_user_xmpp')
    @mock.patch('core.mail.MailQueue.enqueue_user_email')
    def test_mailqueue_on_db_complete(self, mailq, _):
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

    @mock.patch('core.mail.MailQueue.enqueue_user_email')
    @mock.patch('core.xmppclient.XMPPQueue.enqueue_user_xmpp')
    def test_xmppqueue_on_db_complete(self, xmppq, _):
        self.call_on_db_complete()

        no_watcher_call_args = xmppq.call_args_list[0][0]
        T.assert_equal(['testuser'], no_watcher_call_args[0])
        T.assert_in('for testuser', no_watcher_call_args[1])

        watched_call_args = xmppq.call_args_list[1][0]
        T.assert_equal(['testuser', 'testuser1', 'testuser2'], watched_call_args[0])
        T.assert_in('for testuser (testuser1,testuser2)', watched_call_args[1])


if __name__ == '__main__':
    T.run()
