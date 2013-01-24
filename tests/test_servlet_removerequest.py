from contextlib import nested
import mock

from core import db
from core.util import get_servlet_urlspec
from servlets.removerequest import RemoveRequestServlet
import testing as T

class RemoveRequestServletTest(T.TestCase, T.ServletTestMixin):

    def get_handlers(self):
        return [get_servlet_urlspec(RemoveRequestServlet)]

    def test_removerequest(self):
        results = []

        def on_db_return(success, db_results):
            assert success
            results.extend(db_results.fetchall())

        with nested(
            mock.patch.dict(db.Settings, T.MockedSettings),
            mock.patch.object(
                RemoveRequestServlet,
                "get_current_user",
                return_value="testuser"
            )
        ):
            results = []
            db.execute_cb(db.push_pushcontents.select(), on_db_return)
            num_results_before = len(results)

            uri = "/removerequest?request=1&push=1"
            response = self.fetch(uri)
            T.assert_equal(response.error, None)

            results = []
            db.execute_cb(db.push_pushcontents.select(), on_db_return)
            num_results_after = len(results)

            T.assert_equal(num_results_after, num_results_before - 1, "Request removal failed.")
