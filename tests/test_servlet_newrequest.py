from contextlib import nested
import mock
import urllib

from core import db
from core.util import get_servlet_urlspec
from servlets.newrequest import NewRequestServlet
import testing as T

class NewRequestServletTest(T.TestCase, T.ServletTestMixin, T.FakeDataMixin):

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
                'request-title': 'Test Push Request Title',
                'request-tags': 'super-safe,logs',
                'request-review': 1,
                'request-repo': 'testuser',
                'request-branch': 'super_safe_fix',
                'request-comments': 'No comment',
                'request-description': 'I approve this fix!',
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

            last_req = self.get_requests()[-1]
            T.assert_equal(len(results), last_req['id'])
            T.assert_equal('testuser', last_req['user'])
            T.assert_equal(request['request-repo'], last_req['repo'])
            T.assert_equal(request['request-branch'], last_req['branch'])
            T.assert_equal(request['request-tags'], last_req['tags'])
            T.assert_equal(request['request-comments'], last_req['comments'])
            T.assert_equal(request['request-description'], last_req['description'])


if __name__ == '__main__':
	T.run()
