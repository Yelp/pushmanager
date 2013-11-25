from contextlib import nested
from contextlib import contextmanager

import mock
import pushmanager.testing as T
import types

from core import db
from core.settings import Settings
from core.mail import MailQueue
from core.util import get_servlet_urlspec
from core.xmppclient import XMPPQueue
import pushmanager.servlets.newpush
from pushmanager.servlets.newpush import NewPushServlet
from pushmanager.servlets.newpush import send_notifications

class NewPushServletTest(T.TestCase, T.ServletTestMixin):

    def get_handlers(self):
        return [get_servlet_urlspec(NewPushServlet)]

    def test_newpush(self):
        pushes = []

        def on_db_return(success, db_results):
            assert success
            pushes.extend(db_results.fetchall())

        with nested(
            mock.patch.dict(db.Settings, T.MockedSettings),
            mock.patch.object(NewPushServlet, "get_current_user", return_value = "jblack"),
            mock.patch.object(NewPushServlet, "redirect"),
            mock.patch.object(MailQueue, "enqueue_user_email"),
        ):
            with mock.patch("%s.pushmanager.servlets.newpush.subprocess.call" % __name__) as mocked_call:
                title = "BestPushInTheWorld"
                branch = "jblack"
                push_type = "regular"

                uri = "/newpush?push-title=%s&branch=%s&push-type=%s" % (
                    title, branch, push_type
                )

                pushes = []
                db.execute_cb(db.push_pushes.select(), on_db_return)
                num_pushes_before = len(pushes)

                response = self.fetch(uri)
                assert response.error == None

                pushes = []
                db.execute_cb(db.push_pushes.select(), on_db_return)
                num_pushes_after = len(pushes)

                T.assert_equal(num_pushes_before + 1, num_pushes_after)

                # There should be one call to nodebot after a push is created
                T.assert_equal(pushmanager.servlets.newpush.subprocess.call.call_count, 1)

                # Verify that we have a valid call to
                # subprocess.call. Getting the arguments involves ugly
                # mock magic
                mocked_call.assert_called_once_with([
                    '/nail/sys/bin/nodebot',
                    '-i',
                    mock.ANY, # nickname
                    mock.ANY, # channel
                    mock.ANY, # msg
                ])



    def call_on_db_complete(self, urgent=False):
        mocked_self = mock.Mock()
        mocked_self.check_db_results = mock.Mock(return_value=None)
        mocked_self.redirect = mock.Mock(return_value=None)
        mocked_self.pushtype = 'normal'

        mocked_self.on_db_complete = types.MethodType(NewPushServlet.on_db_complete.im_func, mocked_self)

        push = mock.Mock()
        push.lastrowid = 0

        no_watcher_req = {
            'user': 'testuser',
            'watchers': None,
        }
        watched_req = {
            'user': 'testuser',
            'watchers': 'testuser1,testuser2',
        }
        if urgent:
            no_watcher_req['tags'] = 'urgent'
            watched_req['tags'] = 'urgent'
            mocked_self.pushtype = 'urgent'

        reqs = [no_watcher_req, watched_req]

        mocked_self.on_db_complete('success', [push, reqs])

    @mock.patch('pushmanager.servlets.newpush.send_notifications')
    def test_normal_people_on_db_complete(self, notify):
        self.call_on_db_complete()
        notify.called_once_with(set(['testuser', 'testuser1', 'testuser2']), mock.ANY, mock.ANY)

    @mock.patch('pushmanager.servlets.newpush.send_notifications')
    def test_urgent_people_on_db_complete(self, notify):
        self.call_on_db_complete(urgent=True)
        notify.called_once_with(set(['testuser', 'testuser1', 'testuser2']), mock.ANY, mock.ANY)


class NotificationsTestCase(T.TestCase):

    @contextmanager
    def mocked_notifications(self):
        with mock.patch("%s.pushmanager.servlets.newpush.subprocess.call" % __name__) as mocked_call:
            with mock.patch.object(MailQueue, "enqueue_user_email") as mocked_mail:
                with mock.patch.object(XMPPQueue, "enqueue_user_xmpp") as mocked_xmpp:
                    yield mocked_call, mocked_mail, mocked_xmpp

    def test_send_notifications(self):
        """New push sends notifications via IRC, XMPP and emails."""
        self.people = ["fake_user1", "fake_user2"]
        self.pushurl = "/fake_push_url?id=123"
        self.pushtype = "fake_puth_type"

        with self.mocked_notifications() as (mocked_call, mocked_mail, mocked_xmpp):
            send_notifications(self.people, self.pushtype, self.pushurl)

            url = "https://%s%s" % (Settings['main_app']['servername'], self.pushurl)
            msg = "%s: %s push starting! %s" % (', '.join(self.people), self.pushtype, url)
            mocked_call.assert_called_once_with([
                '/nail/sys/bin/nodebot',
                '-i',
                Settings['irc']['nickname'],
                Settings['irc']['channel'],
                msg
            ])
            mocked_mail.assert_called_once_with(
                Settings['mail']['notifyall'],
                msg,
                mock.ANY, # subject
            )
            mocked_xmpp.assert_called_once_with(
                self.people,
                "Push starting! %s" % url
            )

    def test_send_notifications_empty_user_list(self):
        """If there is no pending push request we'll only send IRC and
        email notifications, but not XMPP messages."""
        self.people = []
        self.pushurl = "fake_push_url"
        self.pushtype = "fake_puth_type"

        with self.mocked_notifications() as (mocked_call, mocked_mail, mocked_xmpp):
            send_notifications(self.people, self.pushtype, self.pushurl)
            mocked_call.assert_called_once_with([
                '/nail/sys/bin/nodebot',
                '-i',
                Settings['irc']['nickname'],
                Settings['irc']['channel'],
                mock.ANY, # msg
            ])
            mocked_mail.assert_called_once_with(
                Settings['mail']['notifyall'],
                mock.ANY, # msg
                mock.ANY, # subject
            )
            T.assert_is(mocked_xmpp.called, False)


if __name__ == '__main__':
    T.run()
