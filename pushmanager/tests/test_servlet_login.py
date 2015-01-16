from contextlib import nested
import mock
import logging
import urllib

import testify as T
from pushmanager.handlers import LoginHandler
from pushmanager.testing.testservlet import ServletTestMixin


class LoginTest(T.TestCase, ServletTestMixin):

    def get_handlers(self):
        return [(r'/login', LoginHandler)]

    def test_no_strategy_login_post(self):
        request = {
            "username": "fake_username",
            "password": "fake_password"
        }
        T.MockedSettings['login_strategy'] = ''
        with nested(mock.patch.object(logging, "exception"),
                    mock.patch.dict(Settings, T.MockedSettings)):

            response = self.fetch(
                "/login",
                method="POST",
                body=urllib.urlencode(request)
            )
            T.assert_in("No login strategy currently configured.", response.body)

    def test_ldap_login_post(self):
        request = {
            "username": "fake_username",
            "password": "fake_password"
        }
        T.MockedSettings['login_strategy'] = 'ldap'
        with nested(mock.patch.object(logging, "exception"),
                    mock.patch.dict(Settings, T.MockedSettings)):

            response = self.fetch(
                "/login",
                method="POST",
                body=urllib.urlencode(request)
            )
            T.assert_in("Invalid username or password specified.", response.body)

    def test_saml_login_post(self):
        T.MockedSettings['login_strategy'] = 'saml'
        with nested(mock.patch.object(logging, "exception"),
                    mock.patch.dict(Settings, T.MockedSettings)):
            with mock.patch("pushmanager_main.LoginHandler._saml_login") as mock_saml_login:

                request = {}
                self.fetch(
                    "/login",
                    method="POST",
                    body=urllib.urlencode(request)
                )
                mock_saml_login.assert_called()
