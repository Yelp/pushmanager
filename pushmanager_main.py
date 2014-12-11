#!/usr/bin/python
from __future__ import with_statement
import os
import urlparse

from onelogin.saml2.auth import OneLogin_Saml2_Auth as authenticate_saml
import tornado.httpserver
import tornado.web


from core.application import Application
from core.auth import authenticate_ldap
import core.db as db
from core.git import GitQueue
from core.mail import MailQueue
from core.rb import RBQueue
from core.requesthandler import RequestHandler
from core.settings import Settings
from core.util import get_servlet_urlspec
from core.xmppclient import XMPPQueue
from servlets.addrequest import AddRequestServlet
from servlets.api import APIServlet
from servlets.checklist import ChecklistServlet
from servlets.checklist import ChecklistToggleServlet
from servlets.commentrequest import CommentRequestServlet
from servlets.editpush import EditPushServlet
from servlets.newrequest import NewRequestServlet
from servlets.delayrequest import DelayRequestServlet
from servlets.discardpush import DiscardPushServlet
from servlets.discardrequest import DiscardRequestServlet
from servlets.deploypush import DeployPushServlet
from servlets.blesspush import BlessPushServlet
from servlets.livepush import LivePushServlet
from servlets.msg import MsgServlet
from servlets.newpush import NewPushServlet
from servlets.pickmerequest import PickMeRequestServlet, UnpickMeRequestServlet
from servlets.pingme import PingMeServlet
from servlets.push import PushServlet
from servlets.pushbyrequest import PushByRequestServlet
from servlets.pushes import PushesServlet
from servlets.pushitems import PushItemsServlet
from servlets.removerequest import RemoveRequestServlet
from servlets.request import RequestServlet
from servlets.requests import RequestsServlet
from servlets.smartdest import SmartDestServlet
from servlets.summaryforbranch import SummaryForBranchServlet
from servlets.undelayrequest import UndelayRequestServlet
from servlets.userlist import UserListServlet
from servlets.verifyrequest import VerifyRequestServlet

import ui_modules


def prepare_request_for_saml_toolkit(request):
    port = urlparse.urlparse(request.uri).port
    if not port:
        schemes = {"http": 80, "https": 443}
        port = schemes[request.protocol]

    return {
        'http_host': request.host,
        'server_port': port,
        'script_name': request.path,
        'get_data': dict((k, ''.join(v)) for k, v in request.arguments.items()),
        'post_data': dict((k, ''.join(v)) for k, v in request.arguments.items())
    }


def login(request_handler, username, next_url):
    request_handler.set_secure_cookie("user", username)
    return request_handler.redirect(next_url or "/")


def logout(request_handler):
    request_handler.clear_cookie("user")
    return request_handler.redirect("/")


class NullRequestHandler(RequestHandler):
    def get(self): pass
    def post(self): pass


class BookmarkletHandler(RequestHandler):
    bookmarklet = None
    def get(self):
        if self.bookmarklet:
            self.render(self.bookmarklet)


class CreateRequestBookmarkletHandler(BookmarkletHandler):
    bookmarklet = "create_request_bookmarklet.js"
    # Create Request Bookmarklet is served from /bookmarklet to keep backwards compatibility.
    url = r"/bookmarklet"


class CheckSitesBookmarkletHandler(BookmarkletHandler):
    bookmarklet = "check_sites_bookmarklet.js"
    url = r"/checksitesbookmarklet"


class LoginHandler(RequestHandler):
    def get(self):
        next_url = self.request.arguments.get('next', [None])[0]
        if self.current_user:
            return self.redirect(next_url or '/')
        if Settings['login_strategy'] == 'ldap':
            self.render("login.html", page_title="Login", errors=None, next_url=next_url)
        elif Settings['login_strategy'] == 'saml':
            req = prepare_request_for_saml_toolkit(self.request)
            auth = authenticate_saml(req, custom_base_path=Settings['saml_config_folder'])
            return self.redirect(auth.login())
        else:
            return self.render("login.html", page_title="Login", next_url=next_url,
                               errors="No login strategy currently configured. Please have a friendly sysadmin fix this.")

    def post(self):
        next_url = self.request.arguments.get('next', [None])[0]
        username = self.request.arguments.get('username', [None])[0]
        password = self.request.arguments.get('password', [None])[0]

        if self.current_user:
            return self.redirect(next_url or '/')

        if Settings['login_strategy'] == 'ldap':
            # LDAP is our basic auth strategy.
            if not username or not password:
                return self.render("login.html", page_title="Login", next_url=next_url,
                                   errors="Please enter both a username and a password.")
            if not authenticate_ldap(username, password):
                return self.render("login.html", page_title="Login", next_url=next_url,
                                   errors="Invalid username or password specified.")
            login(self, username, next_url)

        elif Settings['login_strategy'] == 'saml':
            # They shouldn't be POSTing, but it's cool. Blatantly ignore their form and redirect them to the IdP to try again.
            # SAML doesn't support friendly redirects to next_url for security, so they'll end up on the landing page after auth.
            return self.redirect(authenticate_saml.login())
        else:
            # TODO: Turn this into an HTTP status code along 4xx
            # Give them the basic auth page with an error telling them logins are currently botched.
            return self.render("login.html", page_title="Login", next_url=next_url,
                               errors="No login strategy currently configured. Please have a friendly sysadmin fix this.")            


class SamlACSHandler(RequestHandler):
    """TODO Handles calls to the SAML service provider consumer assertion endpoint."""
    def post(self):
        req = prepare_request_for_saml_toolkit(self.request)
        auth = authenticate_saml(req, custom_base_path=Settings['saml_config_folder'])
        auth.process_response()
        errors = auth.get_errors()
        if not errors:
            if auth.is_authenticated():
                login(self, str(auth.get_attributes(), "/"))  # TODO: Get an actual username
            else:
                self.render('Not authenticated')  # TODO: Promote these to HTTP status codes with responses
        else:
            self.render("Error when processing SAML Response: %s %s" % (', '.join(errors), auth.get_last_error_reason()))


class LdapLogoutHandler(RequestHandler):
    def get(self):
        logout(self)
    post = get


class SamlSLSHandler(RequestHandler):
    """Handles calls to the SAML service provider single logout endpoint."""
    def get(self):
        req = prepare_request_for_saml_toolkit(self.request)
        auth = authenticate_saml(req, custom_base_path=Settings['saml_config_folder'])
        url = auth.process_slo(delete_session_cb=lambda _: logout(self))
        errors = auth.get_errors()
        if len(errors) == 0:
            if url is not None:
                return HttpResponseRedirect(url)
            else:
                success_slo = True
    post = get  # TODO: just support POST


class RedirHandler(tornado.web.RequestHandler):
    def get(self, path):
        self.redirect(urlparse.urljoin(
            'https://%s/' % Settings['main_app']['servername'],
            path,
        ), permanent=True)
    post = get


# Servlet dispatch rules
def get_url_specs():
    url_specs = [
        (r'/', SmartDestServlet),
        (r'favicon.*', NullRequestHandler),
        (CreateRequestBookmarkletHandler.url, CreateRequestBookmarkletHandler),
        (CheckSitesBookmarkletHandler.url, CheckSitesBookmarkletHandler),
        (r'/login', LoginHandler),
    ]
    if Settings['login_strategy'] == 'ldap':
        url_specs.append((r'/logout', LdapLogoutHandler))
    elif Settings['login_strategy'] == 'saml':
        url_specs.extend([(r'/acs', SamlACSHandler),
                          (r'/sls', SamlSLSHandler)])
    for servlet in (APIServlet,
                    ChecklistServlet,
                    ChecklistToggleServlet,
                    RequestServlet,
                    RequestsServlet,
                    NewRequestServlet,
                    PickMeRequestServlet,
                    UnpickMeRequestServlet,
                    AddRequestServlet,
                    RemoveRequestServlet,
                    VerifyRequestServlet,
                    DiscardRequestServlet,
                    DelayRequestServlet,
                    UndelayRequestServlet,
                    CommentRequestServlet,
                    PingMeServlet,
                    PushServlet,
                    PushesServlet,
                    EditPushServlet,
                    DiscardPushServlet,
                    DeployPushServlet,
                    BlessPushServlet,
                    LivePushServlet,
                    NewPushServlet,
                    PushItemsServlet,
                    PushByRequestServlet,
                    UserListServlet,
                    SummaryForBranchServlet,
                    MsgServlet):
        url_specs.append(get_servlet_urlspec(servlet))
    return url_specs


class PushManagerApp(Application):
    name = "main"

    def __init__(self):
        Application.__init__(self)
        self.redir_port = Settings['main_app']['redir_port']
        self.redir_app = tornado.web.Application(
            [
                (r'/(.*)', RedirHandler),
            ],
        )
        self.main_app = tornado.web.Application(
            get_url_specs(),
            # Server settings
            static_path = os.path.join(os.path.dirname(__file__), "static"),
            template_path = os.path.join(os.path.dirname(__file__), "templates"),
            gzip = True,
            login_url = "/login",
            cookie_secret = Settings['cookie_secret'],
            ui_modules = ui_modules,
            autoescape = None,
        )

    def start_services(self):
        # HTTPS server
        sockets = tornado.netutil.bind_sockets(self.port, address=Settings['main_app']['servername'])
        redir_sockets = tornado.netutil.bind_sockets(self.redir_port, address=Settings['main_app']['servername'])
        tornado.process.fork_processes(0)

        server = tornado.httpserver.HTTPServer(self.main_app, ssl_options={
                'certfile': Settings['main_app']['ssl_certfile'],
                # This really should be read into a string so we can drop privileges
                # after reading the key but before starting the server, but Python
                # doesn't let us use strings for keys until Python 3.2 :(
                'keyfile': Settings['main_app']['ssl_keyfile'],
                })
        server.add_sockets(sockets)

        # HTTP server (to redirect to HTTPS)
        redir_server = tornado.httpserver.HTTPServer(self.redir_app)
        redir_server.add_sockets(redir_sockets)

        # Start the mail, git, reviewboard and XMPP queue handlers
        MailQueue.start_worker()
        GitQueue.start_worker()
        RBQueue.start_worker()
        XMPPQueue.start_worker()

if __name__ == '__main__':
    app = PushManagerApp()
    db.init_db()
    app.run()
