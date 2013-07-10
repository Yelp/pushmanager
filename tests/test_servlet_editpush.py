from mock import patch
import urllib

from core import db
from core.util import get_servlet_urlspec
from servlets.editpush import EditPushServlet
import testing as T


class EditPushServletTest(T.TestCase, T.ServletTestMixin, T.FakeDataMixin):

    def get_handlers(self):
        return [get_servlet_urlspec(EditPushServlet)]

    @patch.dict(db.Settings, T.MockedSettings)
    @patch.object(EditPushServlet, 'redirect')
    @patch.object(EditPushServlet, 'get_current_user', return_value='testuser')
    def test_editpush(self, *_):
        results = []

        def on_db_return(success, db_results):
            assert success
            results.extend(db_results.fetchall())

        results = []
        db.execute_cb(db.push_pushes.select(), on_db_return)
        num_results_before = len(results)

        existing_push = self.get_pushes()[0]
        print existing_push

        push = {
            'id':  existing_push[0],
            'push-title': 'clever-title',
            'push-branch': 'deploy-clever-branch',
            }

        response = self.fetch(
            '/editpush',
            method='POST',
            body=urllib.urlencode(push)
        )
        T.assert_equal(response.error, None)

        results = []
        db.execute_cb(db.push_pushes.select(), on_db_return)
        num_results_after = len(results)

        T.assert_equal(num_results_after, num_results_before)

        existing_push = self.get_pushes()[0]
        T.assert_equal(existing_push[1], push['push-title'])
        T.assert_equal(existing_push[2], 'testuser')
        T.assert_equal(existing_push[3], push['push-branch'])
