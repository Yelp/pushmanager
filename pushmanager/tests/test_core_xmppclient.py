from contextlib import contextmanager
from contextlib import nested

import mock

from pushmanager.testing.mocksettings import MockedSettings
import core.xmppclient
import pushmanager.testing as T

class CoreXMPPClientTest(T.TestCase):

    @T.setup
    def setup_fakexmpp_attrs(self):
        self.fake_client_attrs = {
            "auth.return_value": True,
            "connect.return_value": True,
            "disconnect.return_value": True,
            "isConnected.return_value": True,
            "Process.return_value": True,
            "reconnectAndReauth.return_value": True,
            "send.return_value": True,
            "sendInitPresence.return_value": True
        }

        self.fake_queue_attrs = {
            "get.return_value": ('testuser@example.com', "Fake Message")
        }

    @contextmanager
    def fake_xmpp_connect(self):
        with nested(
            mock.patch("%s.core.xmppclient.logging" % __name__),
            mock.patch("%s.core.xmppclient.Settings" % __name__),
            mock.patch("%s.core.xmppclient.xmpp.Client" % __name__),
            mock.patch("%s.core.xmppclient.xmpp.protocol.JID" % __name__),
        ):
            core.xmppclient.xmpp.Client.configure_mock(**self.fake_client_attrs)
            jabber_client = core.xmppclient.XMPPQueue._xmpp_connect_and_auth()
            yield jabber_client

    def test_xmpp_connect(self):
        with self.fake_xmpp_connect() as jabber_client:
            T.assert_equal(jabber_client.connect.call_count, 1)
            T.assert_equal(jabber_client.auth.call_count, 1)

    def test_xmpp_reconnect(self):
        with self.fake_xmpp_connect() as jabber_client:
            jabber_client.isConnected.return_value = False
            core.xmppclient.XMPPQueue._xmpp_check_and_reconnect(jabber_client)
            T.assert_equal(jabber_client.reconnectAndReauth.call_count, 1)

    def test_process_queue_item_successful(self):
        with nested(
            mock.patch("%s.core.xmppclient.xmpp.Message" % __name__),
            mock.patch("%s.core.xmppclient.XMPPQueue.message_queue" % __name__)
        ):
            jabber_client = mock.MagicMock()
            core.xmppclient.XMPPQueue.message_queue.configure_mock(**self.fake_queue_attrs)

            core.xmppclient.XMPPQueue._process_queue_item(jabber_client)

            T.assert_equal(jabber_client.send.call_count, 1)
            T.assert_equal(core.xmppclient.XMPPQueue.message_queue.get.call_count, 1)
            T.assert_equal(core.xmppclient.XMPPQueue.message_queue.put.call_count, 0)
            T.assert_equal(core.xmppclient.XMPPQueue.message_queue.task_done.call_count, 1)

    def test_process_queue_item_retry(self):
        def raise_ioerror(*args):
            raise IOError("Fake IOError")

        with nested(
            mock.patch("%s.core.xmppclient.logging" % __name__),
            mock.patch("%s.core.xmppclient.xmpp.Message" % __name__),
            mock.patch("%s.core.xmppclient.XMPPQueue.message_queue" % __name__)
        ):
            jabber_client = mock.MagicMock()
            jabber_client.send.side_effect = raise_ioerror
            core.xmppclient.XMPPQueue.message_queue.configure_mock(**self.fake_queue_attrs)

            # Try sending the same message more than max_retry_count
            retry_count = core.xmppclient.XMPPQueue.MAX_RETRY_COUNT

            for _ in range(retry_count):
                core.xmppclient.XMPPQueue._process_queue_item(jabber_client)

            T.assert_equal(jabber_client.send.call_count, retry_count)
            T.assert_equal(core.xmppclient.XMPPQueue.message_queue.get.call_count, retry_count)
            T.assert_equal(core.xmppclient.XMPPQueue.message_queue.task_done.call_count, retry_count)
            T.assert_equal(core.xmppclient.XMPPQueue.message_queue.put.call_count, retry_count - 1)

    def test_enqueue_user_xmpp_with_string(self):
        fake_domain = "fakedomain.com"
        fake_user = "fakeuser"
        MockedSettings['xmpp'] = {'default_domain': fake_domain}
        with mock.patch.dict(core.xmppclient.Settings, MockedSettings):
            with mock.patch.object(core.xmppclient.XMPPQueue, "enqueue_xmpp") as mock_enqueue_xmpp:
                core.xmppclient.XMPPQueue.enqueue_user_xmpp(fake_user)
                mock_enqueue_xmpp.assert_called_with("%s@%s" % (fake_user, fake_domain))


    def test_enqueue_user_xmpp_with_list(self):
        fake_domain = "fakedomain.com"
        fake_users = ["fakeuser1", "fakeuser2"]
        MockedSettings['xmpp'] = {'default_domain': fake_domain}
        with mock.patch.dict(core.xmppclient.Settings, MockedSettings):
            with mock.patch.object(core.xmppclient.XMPPQueue, "enqueue_xmpp") as mock_enqueue_xmpp:
                core.xmppclient.XMPPQueue.enqueue_user_xmpp(fake_users)
                fake_ids = ["%s@%s" % (fake_user, fake_domain) for fake_user in fake_users]
                mock_enqueue_xmpp.assert_called_with(fake_ids)
