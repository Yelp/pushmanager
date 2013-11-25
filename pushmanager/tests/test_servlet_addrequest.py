from contextlib import nested
import mock
import urllib

from core import db
from core.util import get_servlet_urlspec
from pushmanager.servlets.addrequest import AddRequestServlet
import pushmanager.testing as T
import types

class AddRequestServletTest(T.TestCase, ServletTestMixin):

    @T.class_setup_teardown
    def mock_servlet_env(self):
        self.results = []
        with nested(
            mock.patch.dict(db.Settings, MockedSettings),
            mock.patch.object(
                AddRequestServlet,
                "get_current_user",
                return_value="testuser"
            )
        ):
            yield

    def record_pushcontents(self, success, db_results):
        assert success
        self.results = []
        self.results.extend(db_results.fetchall())

    def get_handlers(self):
        return [get_servlet_urlspec(AddRequestServlet)]

    def test_add_existing_request(self):
        db.execute_cb(db.push_pushcontents.select(), self.record_pushcontents)
        num_results_before = len(self.results)

        request = { 'request': 1, 'push': 1 }
        response = self.fetch(
            '/addrequest',
            method='POST',
            body=urllib.urlencode(request)
        )
        T.assert_equal(response.error, None)

        db.execute_cb(db.push_pushcontents.select(), self.record_pushcontents)
        num_results_after = len(self.results)
        T.assert_equal(num_results_after, num_results_before, "Add existing request failed.")

    def test_add_new_request(self):
        db.execute_cb(db.push_pushcontents.select(), self.record_pushcontents)
        num_results_before = len(self.results)

        request = { 'request': 2, 'push': 1 }
        response = self.fetch(
            '/addrequest',
            method='POST',
            body=urllib.urlencode(request)
        )
        T.assert_equal(response.error, None)

        db.execute_cb(db.push_pushcontents.select(), self.record_pushcontents)
        num_results_after = len(self.results)
        T.assert_equal(num_results_after, num_results_before + 1, "Add new request failed.")

    @mock.patch('core.db.execute_transaction_cb')
    def test_pushcontent_insert_ignore(self, mock_transaction):
        request = { 'request': 1, 'push': 1 }
        response = self.fetch(
            '/addrequest',
            method='POST',
            body=urllib.urlencode(request)
        )
        T.assert_equal(response.error, None)
        T.assert_equal(mock_transaction.call_count, 1)

        # Extract the string of the prefix of the insert query
        insert_ignore_clause = mock_transaction.call_args[0][0][0]
        T.assert_is(type(insert_ignore_clause), db.InsertIgnore)

    def call_on_db_complete(self):
        mocked_self = mock.Mock()
        mocked_self.current_user = 'fake_pushmaster'
        mocked_self.pushid = 0
        mocked_self.check_db_results = mock.Mock(return_value=None)

        mocked_self.on_db_complete = types.MethodType(AddRequestServlet.on_db_complete.im_func, mocked_self)

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

        mocked_self.on_db_complete('success', [None, reqs])

    @mock.patch('core.xmppclient.XMPPQueue.enqueue_user_xmpp')
    @mock.patch('core.mail.MailQueue.enqueue_user_email')
    def test_mailqueue_on_db_complete(self, mailq, _):
        self.call_on_db_complete()

        no_watcher_call_args = mailq.call_args_list[0][0]
        T.assert_equal(['testuser'], no_watcher_call_args[0])
        T.assert_in('for testuser', no_watcher_call_args[1])
        T.assert_in('testuser - title', no_watcher_call_args[1])
        T.assert_in('[push] testuser - title', no_watcher_call_args[2])

        watched_call_args = mailq.call_args_list[1][0]
        T.assert_equal(['testuser', 'testuser1', 'testuser2'], watched_call_args[0])
        T.assert_in('for testuser (testuser1,testuser2)', watched_call_args[1])
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
