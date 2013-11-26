import contextlib
import mock

from pushmanager_main import CreateRequestBookmarkletHandler
from pushmanager_main import CheckSitesBookmarkletHandler
import testing as T


class BookmarkletTest(T.TestCase, T.AsyncTestCase):

    def get_handlers(self):
        return [
            (CreateRequestBookmarkletHandler.url, CreateRequestBookmarkletHandler),
            (CheckSitesBookmarkletHandler.url, CheckSitesBookmarkletHandler),
        ]

    @contextlib.contextmanager
    def page(self, handler):
        with mock.patch.object(handler, "get_current_user"):
            handler.get_current_user.return_value = "testuser"
            response = self.fetch(str(handler.url))
            yield response

    def test_create_request_bookmarklet(self):
        with self.page(CreateRequestBookmarkletHandler) as response:
            # We'll get a javascript as the body, just check some
            # variable names/strings that we know is there in the
            # script.
            T.assert_equal(response.error, None)
            T.assert_in("ticketNumberToURL", response.body)
            T.assert_in("codeReview", response.body)


    def test_check_sites_bookmarklet(self):
        with self.page(CheckSitesBookmarkletHandler) as response:
            # See comment above in test_create_request_bookmarklet
            T.assert_equal(response.error, None)
            T.assert_in("window.open", response.body)
