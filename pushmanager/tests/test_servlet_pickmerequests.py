from contextlib import contextmanager
from contextlib import nested
import mock

from core import db
from core.util import get_servlet_urlspec
from pushmanager.servlets.pickmerequest import PickMeRequestServlet
import pushmanager.testing as T

class PickMeRequestServletTest(T.TestCase, T.ServletTestMixin):

    def get_handlers(self):
        return [get_servlet_urlspec(PickMeRequestServlet)]

    @contextmanager
    def fake_pickme_request(self):
        with nested(
            mock.patch.dict(db.Settings, T.MockedSettings),
            mock.patch.object(
                PickMeRequestServlet,
                "get_current_user",
                return_value = "test_user"
            )
        ):
            yield

    @contextmanager
    def fake_pickme_request_ignore_error(self):
        with nested(
            self.fake_pickme_request(),
            mock.patch("%s.db.logging.error" % __name__)
        ):
            yield

    def test_pickmerequest(self):
        push_contents = []
        def on_db_return(success, db_results):
            assert success
            push_contents.extend(db_results.fetchall())

        with self.fake_pickme_request():
            pushid = 1
            requestid = 2

            push_contents = []
            db.execute_cb(db.push_pushcontents.select(), on_db_return)
            num_contents_before = len(push_contents)

            uri = "/pickmerequest?push=%d&request=%d" % (pushid, requestid)
            response = self.fetch(uri)
            T.assert_equal(response.error, None)

            push_contents = []
            db.execute_cb(db.push_pushcontents.select(), on_db_return)
            num_contents_after = len(push_contents)

            T.assert_equal(num_contents_before + 1, num_contents_after)

    def test_pushcontents_duplicate_key(self):
        with self.fake_pickme_request_ignore_error():
            # push_pushcontents table should define a multi column
            # primary key on (request id, push id).
            #
            # Fake data from T.ServletTestMixin already have this
            # (pushid, requestid) binding. Adding another pickme request
            # with same (request id, push id) should fail.
            requestid = 1
            pushid = 1

            uri = "/pickmerequest?push=%d&request=%d" % (pushid, requestid)
            response = self.fetch(uri)
            T.assert_not_equal(response.error, None)

    def test_duplicate_pickmerequest(self):
        with self.fake_pickme_request_ignore_error():
            # Pickme request shoud not be on two valid
            # pushes. Allowing so would create confusion when/if a
            # pushmaster accepts the request in a push.
            pushid = 1
            duplicate_pushid = 2
            requestid = 2

            response = self.fetch("/pickmerequest?push=%d&request=%d" % (pushid, requestid))
            T.assert_equal(response.error, None)

            response = self.fetch("/pickmerequest?push=%d&request=%d" % (duplicate_pushid, requestid))
            T.assert_not_equal(response.error, None)
