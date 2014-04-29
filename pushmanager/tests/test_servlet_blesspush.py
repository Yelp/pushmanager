from contextlib import nested
import mock

from pushmanager.core import db
from pushmanager.core.util import get_servlet_urlspec
from pushmanager.servlets.blesspush import BlessPushServlet
from pushmanager.testing.mocksettings import MockedSettings
from pushmanager.testing.testservlet import ServletTestMixin
import pushmanager.testing as T
import types

class BlessPushServletTest(T.TestCase, ServletTestMixin):

    @T.class_setup_teardown
    def mock_servlet_env(self):
        self.results = []
        with nested(
            mock.patch.dict(db.Settings, MockedSettings),
            mock.patch.object(
                BlessPushServlet,
                "get_current_user",
                return_value="testuser"
            )
        ):
            yield

    def get_handlers(self):
        return [get_servlet_urlspec(BlessPushServlet)]

    def call_on_db_complete(self):
        mocked_self = mock.Mock()
        mocked_self.current_user = 'fake_pushmaster'
        mocked_self.pushid = 0
        mocked_self.check_db_results = mock.Mock(return_value=None)

        mocked_self.on_db_complete = types.MethodType(BlessPushServlet.on_db_complete.im_func, mocked_self)

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
            return {'extra_pings': None}

        res = mock.Mock()
        res.fetchone = fetchone

        mocked_self.on_db_complete('success', [None, reqs, res])


    @mock.patch('pushmanager.core.xmppclient.XMPPQueue.enqueue_user_xmpp')
    @mock.patch('pushmanager.core.mail.MailQueue.enqueue_user_email')
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

    @mock.patch('pushmanager.core.mail.MailQueue.enqueue_user_email')
    @mock.patch('pushmanager.core.xmppclient.XMPPQueue.enqueue_user_xmpp')
    def test_xmppqueue_on_db_complete(self, xmppq, _):
        self.call_on_db_complete()

        no_watcher_call_args = xmppq.call_args_list[0][0]
        T.assert_equal(['testuser'], no_watcher_call_args[0])
        T.assert_in('for testuser', no_watcher_call_args[1])
        T.assert_in('for testuser', no_watcher_call_args[1])

        watched_call_args = xmppq.call_args_list[1][0]
        T.assert_equal(['testuser', 'testuser1', 'testuser2'], watched_call_args[0])
        T.assert_in('for testuser (testuser1,testuser2)', watched_call_args[1])


if __name__ == '__main__':
    T.run()
