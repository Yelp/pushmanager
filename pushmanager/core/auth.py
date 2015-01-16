# -*- coding: utf-8 -*-
import logging
import os

import ldap

from pushmanager.core.settings import Settings


os.environ['LDAPTLS_REQCERT'] = 'demand'
os.environ['LDAPTLS_CACERT'] = Settings['auth_ldap']['cert_file']

LDAP_URL = Settings['auth_ldap']['url']


def authenticate_ldap(username, password):
    """Attempts to bind a given username/password pair in LDAP and returns whether or not it succeeded."""
    try:
        dn = "%s@%s" % (username, Settings['auth_ldap']['domain'])
        basedn = Settings['auth_ldap']['basedn']

        con = ldap.initialize(LDAP_URL)

        con.set_option(ldap.OPT_NETWORK_TIMEOUT, 3)
        con.set_option(ldap.OPT_REFERRALS, 0)
        con.set_option(ldap.OPT_PROTOCOL_VERSION, ldap.VERSION3)

        con.start_tls_s()
        try:
            con.simple_bind_s(dn, password)
            con.search_s(basedn, ldap.SCOPE_ONELEVEL)
        except:
            return False
        con.unbind_s()
        return True
    except:
        # Tornado will log POST data in case of an uncaught
        # exception. In this case POST data will have username &
        # password and we do not want it.
        logging.exception("Authentication error")
        return False


__all__ = ['authenticate_ldap', 'authenticate_saml']
