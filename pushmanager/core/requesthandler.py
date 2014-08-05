import contextlib
import json
import urllib
import urlparse

import tornado.httpclient
import tornado.stack_context
import tornado.web
from pushmanager.core.settings import JSSettings
from pushmanager.core.settings import Settings


@contextlib.contextmanager
def async_api_call_error():
    try:
        yield
    except Exception as e:
        if e[0] == "Stream is closed":
            # Client drops request before waiting for a response. You
            # can have this using Chrome pressing CTRL+r/Cmd+r
            # continuously. No need to log this as an error.
            pass
        else:
            raise

class RequestHandler(tornado.web.RequestHandler):

    def get_current_user(self):
        return self.get_secure_cookie("user")

    @staticmethod
    def get_api_page(method):
        host = "%s:%d" % (
                    Settings['api_app']['servername'],
                    Settings['api_app']['port'],
                )
        path = "api/%s" % method
        return urlparse.urlunsplit((
                    "http",
                    host,
                    path,
                    '',
                    ''
                ))

    def async_api_call(self, method, arguments, callback):
        self.http = tornado.httpclient.AsyncHTTPClient()
        with tornado.stack_context.StackContext(async_api_call_error):
            self.http.fetch(
                self.get_api_page(method),
                callback,
                method="POST",
                body=urllib.urlencode(arguments)
            )

    def get_api_results(self, response):
        if response.error:
            return self.send_error()

        try:
            return json.loads(response.body)
        except ValueError:
            return self.send_error(500)

    def check_db_results(self, success, db_results):
        assert success, "Database error."

    def render(self, templ, **kwargs):
        # These are passed to templates and JSSettings should have
        # enough configuration information for templates too. Just
        # binding JSSettings as Settings and letting templates to use
        # it. JSSetting is just a subset of the Settings dictionary
        # and is safe to pass around.
        kwargs.setdefault('Settings', JSSettings)
        kwargs.setdefault('JSSettings_json', json.dumps(JSSettings, sort_keys=True))
        super(RequestHandler, self).render(templ, **kwargs)


__all__ = ['RequestHandler']
