#!/usr/bin/env python

import mock
import testify as T

from pushmanager.core.settings import Settings
from pushmanager.core.requesthandler import RequestHandler
from pushmanager.testing.mocksettings import MockedSettings

class RequestHandlerTest(T.TestCase):

    def test_get_api_page(self):
        MockedSettings['api_app'] = {'port': 8043, 'servername': 'push.test.com'}
        with mock.patch.dict(Settings, MockedSettings):
            T.assert_equal(
                RequestHandler.get_api_page("pushes"),
                "http://push.test.com:8043/api/pushes"
            )
