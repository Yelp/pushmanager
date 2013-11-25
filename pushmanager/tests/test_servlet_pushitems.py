import contextlib
import json
import mock

from core.util import get_servlet_urlspec
from pushmanager.servlets.pushitems import PushItemsServlet
import pushmanager.testing as T

class PushsItemsServletTest(T.TestCase, T.ServletTestMixin):

    def get_handlers(self):
        return [
            get_servlet_urlspec(PushItemsServlet),
        ]

    @T.setup
    def setup_fake_requests_response(self):
        self.fake_request_data = {
            "created": 1346458663.2721,
            "title": "One Push",
            "modified": 1346458663.2721,
            "tags": "fake_tag1,fake_tag2",
            "user": "drseuss",
            "repo": "drseuss",
            "comments": "No comment",
            "branch": "fake_branchname",
            "reviewid": 10,
            "id": 1
        }
        self.fake_requests_response = "[%s]" % json.dumps(self.fake_request_data)


    def test_pushitems(self):
        with contextlib.nested(
            mock.patch.object(PushItemsServlet, "get_current_user", return_value=self.fake_request_data["user"]),
            mock.patch.object(PushItemsServlet, "async_api_call", side_effect=self.mocked_api_call),
            mock.patch.object(self, "api_response", return_value=self.fake_requests_response)
        ):
            self.fetch("/pushitems?push=%d" % self.fake_request_data["id"])
            response = self.wait()
            T.assert_in(self.fake_request_data["title"], response.body)
