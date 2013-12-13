#!/usr/bin/env python
from __future__ import with_statement
import os
import tornado.httpserver
import tornado.process

from pushmanager.core.application import Application
import pushmanager.core.db as db
from pushmanager.core.settings import Settings
from pushmanager.core.util import get_servlet_urlspec
from pushmanager.servlets.api import APIServlet
import pushmanager.ui_modules as ui_modules

api_application = tornado.web.Application(
    # Servlet dispatch rules
    [
        get_servlet_urlspec(APIServlet),
    ],
    # Server settings
    static_path = os.path.join(os.path.dirname(__file__), "static"),
    template_path = os.path.join(os.path.dirname(__file__), "templates"),
    gzip = True,
    login_url = "/login",
    cookie_secret = Settings['cookie_secret'],
    ui_modules = ui_modules,
    autoescape = None,
)

class PushManagerAPIApp(Application):
    name = "api"

    def start_services(self):
        # HTTP server (for api)
        sockets = tornado.netutil.bind_sockets(self.port, address=Settings['api_app']['servername'])
        tornado.process.fork_processes(Settings['tornado']['num_workers'])
        server = tornado.httpserver.HTTPServer(api_application)
        server.add_sockets(sockets)

if __name__ == '__main__':
    app = PushManagerAPIApp()
    db.init_db()
    app.run()
