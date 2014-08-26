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

    def test_msg_servlet_no_people(self):
        resp = self.fetch('/msg', method='POST', body='message=foo')
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

    def test_servlet_with_people(self):
        resp = self.fetch(
            '/msg',
            method='POST',
            body='message=foo&people[]=asottile&people[]=milki',
        )
        T.assert_is(resp.error, None)
        self.call_mock.assert_called_once_with(
            [
                '/nail/sys/bin/nodebot',
                '-i',
                mock.ANY,
                mock.ANY,
                '[[pushmaster testuser]] asottile, milki: foo',
            ],
        )

    def test_servlet_with_multiple_people(self):
        """Test multiple names

        When we have lots of names, pushmanager should send multiple
        announcements instead of a single large annoucement.
        """

        people = [
            'asottile', 'milki', 'smoy', 'spatel', 'tdoran',
            'tkadich1', 'tzhu', 'vpadmana', 'wtimoney', 'wting',
            'osarood', 'pberens', 'perry', 'plucas',
        ]

        name_list = ''.join(['&people[]=' + person for person in people])
        resp = self.fetch(
            '/msg',
            method='POST',
            body='message=foo' + name_list,
        )
        T.assert_is(resp.error, None)

        groups = [people[i:i+5] for i in range(0, len(people), 5)]
        T.assert_equal(
            self.call_mock.call_count,
            len(groups),
            message='multiple people should be divided into groups'
        )

        for group in groups:
            self.call_mock.assert_any_call(
                [
                    '/nail/sys/bin/nodebot',
                    '-i',
                    mock.ANY,
                    mock.ANY,
                    '[[pushmaster testuser]] ' + (', ').join(group) + ': foo',
                ],
            )


if __name__ == '__main__':
    T.run()
