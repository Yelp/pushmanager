#!/usr/bin/env python
import logging

import mock
import testify as T

from pushmanager.core import auth

class TestAuthenticaton(T.TestCase):

    def test_authenticate(self):
        with mock.patch.object(logging, "exception"):
            T.assert_equal(auth.authenticate("fake_user", "fake_password"), False)
