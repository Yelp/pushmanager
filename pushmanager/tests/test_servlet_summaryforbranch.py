from contextlib import nested
import mock

from core.util import get_servlet_urlspec
from pushmanager.servlets.summaryforbranch import SummaryForBranchServlet
import testing as T

class SummaryForBranchServletTest(T.TestCase, T.ServletTestMixin):

    def get_handlers(self):
        return [
            get_servlet_urlspec(SummaryForBranchServlet),
        ]

    def test_summaryforbranch(self):
        fake_request = """{
            "id": 10,
            "user": "testuser",
            "repo": "testuser",
            "state": "requested",
            "branch": "testuser_fixes",
            "revision": "00000",
            "description": "long desc",
            "title": "funny title",
            "reviewid": 101
        }"""

        with nested(
            mock.patch.object(SummaryForBranchServlet, "get_current_user", return_value="testuser"),
            mock.patch.object(SummaryForBranchServlet, "async_api_call", side_effect=self.mocked_api_call),
            mock.patch.object(self, "api_response", return_value="[%s]" % fake_request),
        ):
            self.fetch("/summaryforbranch?userbranch=testuser/testuser_fixes")
            response = self.wait()
            T.assert_equal(response.error, None)
            T.assert_in("long desc", response.body)

    def test_branch_name_with_slash(self):
        fake_request = """{
            "id": 10,
            "user": "testuser",
            "repo": "testuser",
            "state": "requested",
            "branch": "testuser/testbranch",
            "revision": "00000",
            "description": "description for 'testuser/testbranch'",
            "title": "funny title",
            "reviewid": 102
        }"""

        with nested(
            mock.patch.object(SummaryForBranchServlet, "get_current_user", return_value="testuser"),
            mock.patch.object(SummaryForBranchServlet, "async_api_call", side_effect=self.mocked_api_call),
            mock.patch.object(self, "api_response", return_value="[%s]" % fake_request),
        ):
            self.fetch("/summaryforbranch?userbranch=testuser/testuser/testbranch")
            response = self.wait()
            T.assert_equal(response.error, None)
            T.assert_in("'testuser/testbranch'", response.body)
            T.assert_in("102", response.body)
