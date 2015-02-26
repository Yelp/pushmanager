#!/usr/bin/env python
from __future__ import with_statement

import urlparse

from pushmanager.core.auth import authenticate_ldap
from pushmanager.core.requesthandler import RequestHandler
from pushmanager.core.settings import Settings

# SAML 2.0 support is pluggable, so its presence is optional.
# If SAML auth is requested but the plugin is unavailable, we error.
try:
    from onelogin.saml2.auth import OneLogin_Saml2_Auth as authenticate_saml
except ImportError:
    if Settings['login_strategy'] == 'saml':
        raise ImportError("SAML 2.0 support was requested, but "
                          "onelogin.saml2.auth.OneLogin_Saml2_Auth could not be imported!")


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
            return self._saml_login()
        else:
            return self.render("login.html", page_title="Login", next_url=next_url,
                               errors="No login strategy currently configured. Please have a friendly sysadmin")

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
            return login(self, username, next_url)

        elif Settings['login_strategy'] == 'saml':
            # They shouldn't be POSTing, but it's cool. Blatantly ignore their
            # form and redirect them to the IdP to try again.
            # SAML doesn't support friendly redirects to next_url for security,
            # so they'll end up on the landing page after auth.
            return self._saml_login()

        # TODO: Turn this into an HTTP status code along 4xx
        # Give them the basic auth page with an error telling them logins are currently botched.
        return self.render("login.html", page_title="Login", next_url=next_url,
                           errors="No login strategy currently configured.")

    def _saml_login(self):
        req = prepare_request_for_saml_toolkit(self.request)
        auth = authenticate_saml(req, custom_base_path=Settings['saml_config_folder'])
        return self.redirect(auth.login())


class SamlACSHandler(RequestHandler):
    """Handles calls to the SAML service provider consumer assertion endpoint."""
    def post(self):
        req = prepare_request_for_saml_toolkit(self.request)
        auth = authenticate_saml(req, custom_base_path=Settings['saml_config_folder'])
        auth.process_response()
        errors = auth.get_errors()
        if not errors:
            if auth.is_authenticated():
                login(self, auth.get_attributes()["User.Username"][0], "/")
            else:
                # TODO: Promote these to HTTP status codes with responses
                self.render('Not authenticated')
        else:
            self.render(
                "Error when processing SAML Response: %s %s" % (
                    ', '.join(errors),
                    auth.get_last_error_reason()
                )
            )


class LogoutHandler(RequestHandler):
    def get(self):
        return logout(self)
    post = get


class RedirHandler(RequestHandler):
    def get(self, path):
        self.redirect(urlparse.urljoin(self.get_base_url(), path), permanent=True)
    post = get
