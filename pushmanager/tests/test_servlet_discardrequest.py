import types
from contextlib import nested

import mock
import testify as T
from pushmanager.core import db
from pushmanager.core.util import get_servlet_urlspec
from pushmanager.servlets.discardrequest import DiscardRequestServlet
from pushmanager.testing.mocksettings import MockedSettings
from pushmanager.testing.testservlet import ServletTestMixin


class DiscardRequestServletTest(T.TestCase, ServletTestMixin):

    @T.class_setup_teardown
    def mock_servlet_env(self):
        self.results = []
        with nested(
            mock.patch.dict(db.Settings, MockedSettings),
            mock.patch.object(
                DiscardRequestServlet,
                "get_current_user",
                return_value="testuser"
            )
        ):
            yield

    def get_handlers(self):
        return [get_servlet_urlspec(DiscardRequestServlet)]

    def call_on_db_complete(self, req):
        mocked_self = mock.Mock()
        mocked_self.current_user = 'fake_pushmaster'
        mocked_self.check_db_results = mock.Mock(return_value=None)

        mocked_self.on_db_complete = types.MethodType(DiscardRequestServlet.on_db_complete.im_func, mocked_self)

        def first():
            return req

        mreq = mock.Mock()
        mreq.first = first

        mocked_self.on_db_complete('success', [mock.ANY, mreq])

    @mock.patch('pushmanager.core.mail.MailQueue.enqueue_user_email')
    def test_no_watched_mailqueue_on_db_complete(self, mailq):
        req = {
            'user': 'testuser',
            'watchers': None,
            'repo': 'repo',
            'branch': 'branch',
            'title': 'title',
            'state': 'discarded',
        }
        self.call_on_db_complete(req)

        no_watcher_call_args = mailq.call_args_list[0][0]
        T.assert_equal(['testuser'], no_watcher_call_args[0])
        T.assert_in('Request for testuser', no_watcher_call_args[1])
        T.assert_in('testuser - title', no_watcher_call_args[1])
        T.assert_in('[push] testuser - title', no_watcher_call_args[2])

    @mock.patch('pushmanager.core.mail.MailQueue.enqueue_user_email')
    def test_watched_mailqueue_on_db_complete(self, mailq):
        req = {
            'user': 'testuser',
            'watchers': 'testuser1,testuser2',
            'repo': 'repo',
            'branch': 'branch',
            'title': 'title',
            'state': 'discarded',
        }
        self.call_on_db_complete(req)

        watched_call_args = mailq.call_args_list[0][0]
        T.assert_equal(['testuser', 'testuser1', 'testuser2'], watched_call_args[0])
        T.assert_in('Request for testuser (testuser1,testuser2)', watched_call_args[1])
        T.assert_in('testuser (testuser1,testuser2) - title', watched_call_args[1])
        T.assert_in('[push] testuser (testuser1,testuser2) - title', watched_call_args[2])


if __name__ == '__main__':
    T.run()
