from contextlib import contextmanager
from contextlib import nested

import mock
import testify as T

from pushmanager.testing.mocksettings import MockedSettings
import pushmanager.core.xmppclient


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
            mock.patch("%s.pushmanager.core.xmppclient.logging" % __name__),
            mock.patch("%s.pushmanager.core.xmppclient.Settings" % __name__),
            mock.patch("%s.pushmanager.core.xmppclient.xmpp.Client" % __name__),
            mock.patch("%s.pushmanager.core.xmppclient.xmpp.protocol.JID" % __name__),
        ):
            pushmanager.core.xmppclient.xmpp.Client.configure_mock(**self.fake_client_attrs)
            jabber_client = pushmanager.core.xmppclient.XMPPQueue._xmpp_connect_and_auth()
            yield jabber_client

    def test_xmpp_connect(self):
        with self.fake_xmpp_connect() as jabber_client:
            T.assert_equal(jabber_client.connect.call_count, 1)
            T.assert_equal(jabber_client.auth.call_count, 1)

    def test_xmpp_reconnect(self):
        with self.fake_xmpp_connect() as jabber_client:
            jabber_client.isConnected.return_value = False
            pushmanager.core.xmppclient.XMPPQueue._xmpp_check_and_reconnect(jabber_client)
            T.assert_equal(jabber_client.reconnectAndReauth.call_count, 1)

    def test_process_queue_item_successful(self):
        with nested(
            mock.patch("%s.pushmanager.core.xmppclient.xmpp.Message" % __name__),
            mock.patch("%s.pushmanager.core.xmppclient.XMPPQueue.message_queue" % __name__)
        ):
            jabber_client = mock.MagicMock()
            pushmanager.core.xmppclient.XMPPQueue.message_queue.configure_mock(**self.fake_queue_attrs)

            pushmanager.core.xmppclient.XMPPQueue._process_queue_item(jabber_client)

            T.assert_equal(jabber_client.send.call_count, 1)
            T.assert_equal(pushmanager.core.xmppclient.XMPPQueue.message_queue.get.call_count, 1)
            T.assert_equal(pushmanager.core.xmppclient.XMPPQueue.message_queue.put.call_count, 0)
            T.assert_equal(pushmanager.core.xmppclient.XMPPQueue.message_queue.task_done.call_count, 1)

    def test_process_queue_item_retry(self):
        def raise_ioerror(*args):
            raise IOError("Fake IOError")

        with nested(
            mock.patch("%s.pushmanager.core.xmppclient.logging" % __name__),
            mock.patch("%s.pushmanager.core.xmppclient.xmpp.Message" % __name__),
            mock.patch("%s.pushmanager.core.xmppclient.XMPPQueue.message_queue" % __name__)
        ):
            jabber_client = mock.MagicMock()
            jabber_client.send.side_effect = raise_ioerror
            pushmanager.core.xmppclient.XMPPQueue.message_queue.configure_mock(**self.fake_queue_attrs)

            # Try sending the same message more than max_retry_count
            retry_count = pushmanager.core.xmppclient.XMPPQueue.MAX_RETRY_COUNT

            for _ in range(retry_count):
                pushmanager.core.xmppclient.XMPPQueue._process_queue_item(jabber_client)

            T.assert_equal(jabber_client.send.call_count, retry_count)
            T.assert_equal(pushmanager.core.xmppclient.XMPPQueue.message_queue.get.call_count, retry_count)
            T.assert_equal(pushmanager.core.xmppclient.XMPPQueue.message_queue.task_done.call_count, retry_count)
            T.assert_equal(pushmanager.core.xmppclient.XMPPQueue.message_queue.put.call_count, retry_count - 1)

    def test_enqueue_user_xmpp_with_string(self):
        fake_domain = "fakedomain.com"
        fake_user = "fakeuser"
        MockedSettings['xmpp'] = {'default_domain': fake_domain}
        with mock.patch.dict(pushmanager.core.xmppclient.Settings, MockedSettings):
            with mock.patch.object(pushmanager.core.xmppclient.XMPPQueue, "enqueue_xmpp") as mock_enqueue_xmpp:
                pushmanager.core.xmppclient.XMPPQueue.enqueue_user_xmpp(fake_user)
                mock_enqueue_xmpp.assert_called_with("%s@%s" % (fake_user, fake_domain))


    def test_enqueue_user_xmpp_with_list(self):
        fake_domain = "fakedomain.com"
        fake_users = ["fakeuser1", "fakeuser2"]
        MockedSettings['xmpp'] = {'default_domain': fake_domain}
        with mock.patch.dict(pushmanager.core.xmppclient.Settings, MockedSettings):
            with mock.patch.object(pushmanager.core.xmppclient.XMPPQueue, "enqueue_xmpp") as mock_enqueue_xmpp:
                pushmanager.core.xmppclient.XMPPQueue.enqueue_user_xmpp(fake_users)
                fake_ids = ["%s@%s" % (fake_user, fake_domain) for fake_user in fake_users]
                mock_enqueue_xmpp.assert_called_with(fake_ids)
