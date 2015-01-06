#!/usr/bin/python
import logging

import mock

import testing as T
from core import auth

class TestAuthenticaton(T.TestCase):

    def test_authenticate(self):
        with mock.patch.object(logging, "exception"):
            T.assert_equal(auth.authenticate_ldap("fake_user", "fake_password"), False)
