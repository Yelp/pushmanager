from contextlib import nested
import mock
import urllib

from core import db
from core.util import get_servlet_urlspec
from servlets.addrequest import AddRequestServlet
import testing as T

class AddRequestServletTest(T.TestCase, T.ServletTestMixin):

    @T.class_setup_teardown
    def mock_servlet_env(self):
        self.results = []
        with nested(
            mock.patch.dict(db.Settings, T.MockedSettings),
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
