import logging
import os
import types

import mock
import tornado.web
from lxml import etree
from tornado.testing import AsyncHTTPTestCase
from tornado.web import UIModule

from core import db
from core.requesthandler import RequestHandler
from testify.utils import turtle
import ui_modules
import ui_methods
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
            ui_methods = ui_methods,
            autoescape = None,
        )
        return app


class TemplateTestCase(T.TestCase):
    """Bare minimum setup to render and test templates"""
    __test__ = False

    authenticated = False

    @T.setup
    def setup_servlet(self):
        application = turtle.Turtle()
        application.settings = {
            'static_path': os.path.join(os.path.dirname(__file__), "../static"),
            'template_path': os.path.join(os.path.dirname(__file__), "../templates"),
            'autoescape': None,
        }

        application.ui_modules = {}
        application.ui_methods = {}
        self._load_ui_modules(application, ui_modules)
        self._load_ui_methods(application, ui_methods)

        if self.authenticated:
            application.settings['cookie_secret'] = 'cookie_secret'
        request = turtle.Turtle()
        self.servlet = RequestHandler(application, request)

    def render_etree(self, page, *args, **kwargs):
        self.servlet.render(page, *args, **kwargs)
        rendered_page = ''.join(self.servlet._write_buffer)
        tree = etree.HTML(rendered_page)
        return tree

    # The following methods are lifted from tornado.web.Application
    def _load_ui_methods(self, application, methods):
        if type(methods) is types.ModuleType:
            self._load_ui_methods(
                    application,
                    dict((n, getattr(methods, n)) for n in dir(methods)))
        elif isinstance(methods, list):
            for m in methods:
                self._load_ui_methods(m)
        else:
            for name, fn in methods.iteritems():
                if not name.startswith("_") and hasattr(fn, "__call__") \
                   and name[0].lower() == name[0]:
                    application.ui_methods[name] = fn

    def _load_ui_modules(self, application, modules):
        if type(modules) is types.ModuleType:
            self._load_ui_modules(
                    application,
                    dict((n, getattr(modules, n)) for n in dir(modules)))
        elif isinstance(modules, list):
            for m in modules:
                self._load_ui_modules(m)
        else:
            assert isinstance(modules, dict)
            for name, cls in modules.iteritems():
                try:
                    if issubclass(cls, UIModule):
                        application.ui_modules[name] = cls
                except TypeError:
                    pass


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
