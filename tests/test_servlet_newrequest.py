from contextlib import nested
import mock
import urllib

from core import db
from core.util import get_servlet_urlspec
from servlets.newrequest import NewRequestServlet
import testing as T

class NewRequestServletTest(T.TestCase, T.ServletTestMixin):

    def get_handlers(self):
        return [get_servlet_urlspec(NewRequestServlet)]

    def test_newrequest(self):
        results = []

        def on_db_return(success, db_results):
            assert success
            results.extend(db_results.fetchall())

        with nested(
            mock.patch.dict(db.Settings, T.MockedSettings),
            mock.patch.object(NewRequestServlet, "redirect"),
            mock.patch.object(
                NewRequestServlet,
                "get_current_user",
                return_value="testuser"
            )
        ):
            results = []
            db.execute_cb(db.push_requests.select(), on_db_return)
            num_results_before = len(results)

            request = {
                'title': 'Test Push Request Title',
                'user': 'testuser',
                'tags': 'super-safe,logs',
                'reviewid': 1,
                'repo': 'testuser',
                'branch': 'super_safe_fix',
                'comments': 'No comment',
                'description': 'I approve this fix!',
            }

            response = self.fetch(
                "/newrequest",
                method="POST",
                body=urllib.urlencode(request)
            )
            T.assert_equal(response.error, None)

            results = []
            db.execute_cb(db.push_requests.select(), on_db_return)
            num_results_after = len(results)

            T.assert_equal(num_results_after, num_results_before + 1)
