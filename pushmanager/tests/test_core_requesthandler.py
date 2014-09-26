#!/usr/bin/env python

import mock
import testify as T

import  tornado.httpserver

from pushmanager.core.requesthandler import RequestHandler
from pushmanager.core.requesthandler import get_base_url
from pushmanager.core.settings import Settings
from pushmanager.testing.mocksettings import MockedSettings

class RequestHandlerTest(T.TestCase):

    def test_get_api_page(self):
        MockedSettings['api_app'] = {'port': 8043, 'servername': 'push.test.com'}
        with mock.patch.dict(Settings, MockedSettings):
            T.assert_equal(
                RequestHandler.get_api_page("pushes"),
                "http://push.test.com:8043/api/pushes"
            )

    def test_get_base_url_empty_headers(self):
        MockedSettings['main_app'] = {'port': 1111, 'servername': 'example.com'}
        request = tornado.httpserver.HTTPRequest('GET', '')
        request.protocol = 'https'
        
        with mock.patch.dict(Settings, MockedSettings):
            T.assert_equal(
                get_base_url(request),
                'https://example.com:1111'
            )

            Settings['main_app']['port'] = 443
            T.assert_equal(
                get_base_url(request),
                'https://example.com'
            )

    def test_get_base_url_proto_header(self):
        MockedSettings['main_app'] = {'port': 1111, 'servername': 'example.com'}
        request = tornado.httpserver.HTTPRequest('GET', '')
        request.protocol = 'https'
        request.headers['X-Forwarded-Proto'] = 'http'
        
        with mock.patch.dict(Settings, MockedSettings):
            T.assert_equal(
                get_base_url(request),
                'http://example.com:1111'
            )
            
            Settings['main_app']['port'] = 80
            T.assert_equal(
                get_base_url(request),
                'http://example.com'
            )

    def test_get_base_url_port_header(self):
        MockedSettings['main_app'] = {'port': 1111, 'servername': 'example.com'}
        request = tornado.httpserver.HTTPRequest('GET', '')
        request.protocol = 'https'
        request.headers['X-Forwarded-Port'] = '4321'
        
        with mock.patch.dict(Settings, MockedSettings):
            T.assert_equal(
                get_base_url(request),
                'https://example.com:4321'
            )

            request.headers['X-Forwarded-Port'] = 443
            T.assert_equal(
                get_base_url(request),
                'https://example.com'
            )


    def test_RequestHandler_get_base_url(self):
        MockedSettings['main_app'] = {'port': 1111, 'servername': 'example.com'}
        request = tornado.httpserver.HTTPRequest('GET', '')
        request.protocol = 'https'
        class FakeRequest(object):
            def __init__(self):
                 self.request = request
        
        with mock.patch.dict(Settings, MockedSettings):
            fake_requesthandler = FakeRequest()
            T.assert_equal(
                #Accessing raw, unbound function, so that type of self is not checked
                #http://stackoverflow.com/a/12935356
                RequestHandler.get_base_url.__func__(fake_requesthandler),
                'https://example.com:1111'
            )
