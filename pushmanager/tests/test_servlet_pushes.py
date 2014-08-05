import contextlib

import lxml.html

import mock
import testify as T
from pushmanager.core.util import get_servlet_urlspec
from pushmanager.servlets.pushes import PushesServlet
from pushmanager.testing.testservlet import ServletTestMixin


class PushesServletTest(T.TestCase, ServletTestMixin):

    def get_handlers(self):
        return [
            get_servlet_urlspec(PushesServlet),
        ]

    def find_push_in_response(self, response, title):
        assert response.error is None
        root = lxml.html.fromstring(response.body)
        for elt in root.xpath("//div[@class='push-header']/a"):
            if elt.text.startswith(title):
                return True
        return False

    def test_pushes(self):
        with contextlib.nested(
            mock.patch.object(PushesServlet, "get_current_user"),
            mock.patch.object(PushesServlet, "async_api_call"),
            mock.patch.object(self, "api_response")
        ):
            PushesServlet.get_current_user.return_value = "testuser"
            PushesServlet.async_api_call.side_effect = self.mocked_api_call
            one_push = """{
                    "created": 1346458663.2721,
                    "title": "One Push",
                    "modified": 1346458663.2721,
                    "state": "accepting",
                    "user": "drseuss",
                    "branch": "deploy-second",
                    "extra_pings": null,
                    "pushtype": "private",
                    "id": 1
            }"""
            self.api_response.return_value = "[[%s], 1]" % one_push
            self.fetch("/pushes")
            response = self.wait()
            T.assert_equal(self.find_push_in_response(response, "One Push"), True)
