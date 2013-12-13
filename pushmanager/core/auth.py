# -*- coding: utf-8 -*-
import ldap
import logging
import os

from pushmanager.core.settings import Settings

os.environ['LDAPTLS_REQCERT'] = 'demand'
os.environ['LDAPTLS_CACERT'] = Settings['auth_ldap']['cert_file']

LDAP_URL = Settings['auth_ldap']['url']

def authenticate(username, password):
    """Attempts to bind a given username/password pair in LDAP and returns whether or not it succeeded."""
    try:
        dn = "%s@%s" % (username, Settings['auth_ldap']['domain'])

        con = ldap.initialize(LDAP_URL)

        con.set_option(ldap.OPT_NETWORK_TIMEOUT, 3)
        con.set_option(ldap.OPT_REFERRALS, 0)
        con.set_option(ldap.OPT_PROTOCOL_VERSION, ldap.VERSION3)

        con.start_tls_s()
        try:
            con.simple_bind_s(dn, password)
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

__all__ = ['authenticate']
