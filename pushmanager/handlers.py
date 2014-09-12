#!/usr/bin/env python
from __future__ import with_statement

import urlparse

import tornado.httpserver
import tornado.web
from pushmanager.core.auth import authenticate
from pushmanager.core.requesthandler import RequestHandler
from pushmanager.core.settings import Settings


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
        self.render("login.html", page_title="Login", errors=None, next_url=next_url)

    def post(self):
        next_url = self.request.arguments.get('next', [None])[0]
        username = self.request.arguments.get('username', [None])[0]
        password = self.request.arguments.get('password', [None])[0]

        if self.current_user:
            return self.redirect(next_url or '/')

        if not username or not password:
            return self.render("login.html", page_title="Login", next_url=next_url,
                errors="Please enter both a username and a password.")
        if not authenticate(username, password):
            return self.render("login.html", page_title="Login", next_url=next_url,
                errors="Invalid username or password specified.")

        self.set_secure_cookie("user", username)
        return self.redirect(next_url or "/")


class LogoutHandler(RequestHandler):
    def get(self):
        self.clear_cookie("user")
        return self.redirect("/")
    post = get


class RedirHandler(RequestHandler):
    def get(self, path):
        self.redirect(urlparse.urljoin(get_base_url(), path), permanent=True)
    post = get
