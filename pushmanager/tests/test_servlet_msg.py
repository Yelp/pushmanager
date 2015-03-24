# -*- coding: UTF-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import contextlib
import subprocess

import mock
import testify as T
from pushmanager.core import db
from pushmanager.core.util import get_servlet_urlspec
from pushmanager.servlets.msg import MsgServlet
from pushmanager.testing.mocksettings import MockedSettings
from pushmanager.testing.testservlet import ServletTestMixin

request_with_no_people = [{
        'reviewid': None, 'watchers': u'',
        'description': u'', 'tags': u'', 'created': 1234567890.1234567,
        'modified': 1234567899.1234568, 'comments': u'', 'repo': u'testuser',
        'state': u'added', 'user': u'', 'branch': u'', 'conflicts': None,
        'title': u'testing', 'id': 1, 'revision': u'0'
        }]

request_with_one_people = [{
        'reviewid': None, 'watchers': u'',
        'description': u'', 'tags': u'', 'created': 1234567890.1234567,
        'modified': 1234567899.1234568, 'comments': u'', 'repo': u'testuser',
        'state': u'added', 'user': u'testuser', 'branch': u'', 'conflicts': None,
        'title': u'testing', 'id': 1, 'revision': u'0'
        }]

request_with_watchers = [{
        'reviewid': None, 'watchers': u'testwatcher_1',
        'description': u'', 'tags': u'', 'created': 1234567890.1234567,
        'modified': 1234567899.1234568, 'comments': u'', 'repo': u'testuser',
        'state': u'added', 'user': u'testuser', 'branch': u'', 'conflicts': None,
        'title': u'testing', 'id': 1, 'revision': u'0'
        }]

request_with_message_all = [{
        'reviewid': None, 'watchers': u'',
        'description': u'', 'tags': u'', 'created': 1234567890.1234567,
        'modified': 1234567899.1234568, 'comments': u'', 'repo': u'testuser',
        'state': u'pickme', 'user': u'testuser_1', 'branch': u'', 'conflicts': None,
        'title': u'testing', 'id': 1, 'revision': u'0'
        },
                            {
        'reviewid': None, 'watchers': u'',
        'description': u'', 'tags': u'', 'created': 1234567890.1234567,
        'modified': 1234567899.1234568, 'comments': u'', 'repo': u'testuser',
        'state': u'pickme', 'user': u'testuser_2', 'branch': u'', 'conflicts': None,
        'title': u'testing', 'id': 1, 'revision': u'0'
        },
                            {
        'reviewid': None, 'watchers': u'',
        'description': u'', 'tags': u'', 'created': 1234567890.1234567,
        'modified': 1234567899.1234568, 'comments': u'', 'repo': u'testuser',
        'state': u'verified', 'user': u'testuser_3', 'branch': u'', 'conflicts': None,
        'title': u'testing', 'id': 1, 'revision': u'0'
        }]


class MsgServletTest(T.TestCase, ServletTestMixin):
    @T.setup_teardown
    def mock_logged_in_user(self):
        with contextlib.nested(
            mock.patch.object(subprocess, 'call'),
            mock.patch.object(
                MsgServlet, 'get_current_user', return_value='testuser',
            ),
            mock.patch.dict(db.Settings, MockedSettings),
        ) as (self.call_mock, _, _):
            yield

    def get_handlers(self):
        return [get_servlet_urlspec(MsgServlet)]

    def execute_db_func_with_no_people(query, callback_fn):
        global request_with_no_people
        callback_fn(True, request_with_no_people)

    @mock.patch('pushmanager.servlets.msg.db.execute_cb', side_effect=execute_db_func_with_no_people)
    def test_msg_servlet_for_no_people(self, _):
        resp = self.fetch('/msg', method='POST', body='state=added&message=foo&id=1')
        T.assert_is(resp.error, None)
        self.call_mock.assert_called_once_with(
            [
                '/nail/sys/bin/nodebot',
                '-i',
                mock.ANY,
                mock.ANY,
                '[[pushmaster testuser]] foo',
            ],
        )

    def execute_db_func_with_one_people(query, callback_fn):
        global request_with_one_people
        callback_fn(True, request_with_one_people)

    @mock.patch('pushmanager.servlets.msg.db.execute_cb', side_effect=execute_db_func_with_one_people)
    def test_msg_servlet_for_one_poeple(self, _):
        resp = self.fetch('/msg', method='POST', body='state=added&message=foo&id=1')
        T.assert_is(resp.error, None)
        self.call_mock.assert_called_once_with(
            [
                '/nail/sys/bin/nodebot',
                '-i',
                mock.ANY,
                mock.ANY,
                '[[pushmaster testuser]] testuser: foo',
            ],
        )

    def execute_db_func_with_watchers(query, callback_fn):
        global request_with_watchers
        callback_fn(True, request_with_watchers)

    @mock.patch('pushmanager.servlets.msg.db.execute_cb', side_effect=execute_db_func_with_watchers)
    def test_msg_servlet_for_watchers(self, _):
        resp = self.fetch('/msg', method='POST', body='state=added&message=foo&id=1')
        T.assert_is(resp.error, None)
        call_arguments = self.call_mock.call_args[0][0]
        T.assert_true('/nail/sys/bin/nodebot' in call_arguments[0])
        T.assert_true('-i' in call_arguments[1])
        T.assert_true('testuser' in call_arguments[4])
        T.assert_true('testwatcher_1' in call_arguments[4])
        T.assert_true('foo' in call_arguments[4])

    def execute_db_func_with_message_all(query, callback_fn):
        global request_with_message_all
        callback_fn(True, request_with_message_all)

    @mock.patch('pushmanager.servlets.msg.db.execute_cb', side_effect=execute_db_func_with_message_all)
    def test_msg_servlet_for_message_all(self, _):
        resp = self.fetch('/msg', method='POST', body='state=all&message=foo&id=1')
        T.assert_is(resp.error, None)
        self.call_mock.assert_called_once_with(
            [
                '/nail/sys/bin/nodebot',
                '-i',
                mock.ANY,
                mock.ANY,
                '[[pushmaster testuser]] testuser_3: foo',
            ],
        )

if __name__ == '__main__':
    T.run()
