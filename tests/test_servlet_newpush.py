from contextlib import nested
import mock

from core import db
from core.mail import MailQueue
from core.util import get_servlet_urlspec
import servlets.newpush
from servlets.newpush import NewPushServlet
import testing as T

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
            with mock.patch("%s.servlets.newpush.subprocess.call" % __name__) as mocked_call:
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
                T.assert_equal(servlets.newpush.subprocess.call.call_count, 1)

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
