# -*- coding: utf-8 -*-
import logging
import os

import mock
import tornado.web
from tornado.testing import AsyncHTTPTestCase

from core import db
from testify.utils import turtle
import ui_modules
import testing as T

FORMAT = "%(asctime)-15s %(message)s"
logging.basicConfig(format=FORMAT)

class AsyncTestCase(AsyncHTTPTestCase):

    @T.class_setup
    def setup_async_test_case(self):
        AsyncHTTPTestCase.setUp(self)

    @T.class_teardown
    def teardown_async_test_case(self):
        AsyncHTTPTestCase.tearDown(self)

    def get_handlers(self):
        return None

    def get_app(self):
        app = tornado.web.Application(
            self.get_handlers(),
            static_path = os.path.join(os.path.dirname(__file__), "../static"),
            template_path = os.path.join(os.path.dirname(__file__), "../templates"),
            cookie_secret = 'cookie_secret',
            ui_modules = ui_modules,
            autoescape = None,
        )
        return app


class TemplateTestCase(T.TestCase):
    """Bare minimum setup to render and test templates"""
    __test__ = False

    @T.setup
    def setup_servlet(self):
        application = turtle.Turtle()
        application.settings = {
            'static_path': os.path.join(os.path.dirname(__file__), "../static"),
            'template_path': os.path.join(os.path.dirname(__file__), "../templates"),
            'cookie_secret': 'cookie_secret',
        }
        request = turtle.Turtle()
        self.servlet = self.create_servlet(application, request)

    def create_servlet(self, application, request):
        raise NotImplementedError()


class ServletTestMixin(AsyncTestCase):

    @T.setup
    def setup_db(self):
        self.setup_async_test_case()

        self.db_file = T.make_test_db()
        T.MockedSettings['db_uri'] = T.get_temp_db_uri(self.db_file)
        T.MockedSettings['irc'] = {
            "nickname": "pushhamster+test",
            "channel": "pushmanagertest"
        }
        # for the purpose of unittests we'll use a single application
        # for API and main site.
        T.MockedSettings['api_app'] = {
            "domain": "localhost",
            "port": self.get_http_port()
        }

        with mock.patch.dict(db.Settings, T.MockedSettings):
            db.init_db()

    @T.teardown
    def cleanup_db(self):
        db.finalize_db()
        os.unlink(self.db_file)

    def api_response(self):
        return None

    def mocked_api_call(self, method, arguments, callback):
        """This is the mocked response from API. Responses in tests
        are actually comming from servlets.
        """
        response = mock.MagicMock()
        response.error = None
        response.body = self.api_response()
        callback(response)
        self.stop()
