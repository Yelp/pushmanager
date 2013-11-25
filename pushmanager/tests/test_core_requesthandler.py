#!/usr/bin/env python

import mock

import pushmanager.testing as T
from core.settings import Settings
from core.requesthandler import RequestHandler

class RequestHandlerTest(T.TestCase):

    def test_get_api_page(self):
        MockedSettings['api_app'] = {'port': 8043, 'servername': 'push.test.com'}
        with mock.patch.dict(Settings, MockedSettings):
            T.assert_equal(
                RequestHandler.get_api_page("pushes"),
                "http://push.test.com:8043/api/pushes"
            )
