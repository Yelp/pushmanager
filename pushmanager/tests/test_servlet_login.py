import urllib
import logging

import mock
import testify as T

from pushmanager.handlers import LoginHandler
from pushmanager.testing.testservlet import ServletTestMixin


class LoginTest(T.TestCase, ServletTestMixin):

    def get_handlers(self):
        return [(r'/login', LoginHandler)]

    def test_login_post(self):
        request = {
            "username": "fake_username",
            "password": "fake_password"
        }
        with mock.patch.object(logging, "exception"):
            response = self.fetch(
                "/login",
                method="POST",
                body=urllib.urlencode(request)
            )
            T.assert_in("Invalid username or password specified.", response.body)
