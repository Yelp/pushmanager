import contextlib
import json
import lxml.html
import mock

from core import util
from core.settings import Settings
from pushmanager.servlets.push import PushServlet
import testing as T

class PushServletTestBase(T.TestCase, T.ServletTestMixin, T.FakeDataMixin):
    __test__ = False

    def get_handlers(self):
        return [
            util.get_servlet_urlspec(PushServlet),
        ]

    def find_buildbot_link(self, response, buildbot_link):
        assert response.error is None
        root = lxml.html.fromstring(response.body)
        for elt in root.xpath("//li[@class='tag-buildbot']/a"):
            if elt.attrib['href'] == buildbot_link:
                return True
        return False

    @contextlib.contextmanager
    def request_fake_pushdata(self):
        first_push = self.make_push_dict(self.push_data[0])
        first_request = self.make_request_dict(self.request_data[0])
        first_request['tags'] = "buildbot"
        second_request = self.make_request_dict(self.request_data[1])

        # Prepare pushdata the way PushServlet accepts. This is the
        # format API also replies to pushdata requests.
        pushinfo = util.push_to_jsonable(first_push)
        requests = {
            first_request['state']: [util.request_to_jsonable(first_request)],
            'all': [util.request_to_jsonable(first_request)]
        }
        available_requests = [util.request_to_jsonable(second_request)]

        pushdata = [pushinfo, requests, available_requests]

        with contextlib.nested(
            mock.patch.object(PushServlet, "get_current_user", return_value="testuser"),
            mock.patch.object(PushServlet, "async_api_call", side_effect=self.mocked_api_call),
            mock.patch.object(self, "api_response", return_value=json.dumps(pushdata))
        ):
            self.fetch("/push?id=%d" % first_push['id'])
            response = self.wait()
            yield pushdata, response


class PushServletTest(PushServletTestBase):
    def test_push_with_valid_request(self):
        with self.request_fake_pushdata() as fakepush:
            pushdata, response = fakepush
            T.assert_equal(response.error, None)

    def test_push_buildbot_revision_link(self):
        with self.request_fake_pushdata() as fakepush:
            pushdata, response = fakepush
            T.assert_equal(response.error, None)

            requests = pushdata[1]
            all_requests = requests['all']
            first_request = all_requests[0]
            buildbot_link = "https://%s/rev/%s" % (Settings['buildbot']['servername'], first_request['revision'])
            T.assert_equal(self.find_buildbot_link(response, buildbot_link), True)


class LocalizablesTest(PushServletTestBase):
    def test_push_page_is_using_push_js(self):
        with self.request_fake_pushdata() as fakepush:
            pushdata, response = fakepush
            T.assert_in("js/push.js", response.body)

    def test_localizables_push_website_command_is_correct_in_push_js(self):
        with self.request_fake_pushdata():
            response = self.fetch("/static/js/push.js")
            T.assert_in("localizables_push_website.py", response.body)
            # Old (bash) version of the script shouldn't be there
            T.assert_not_in("localizables-push-website", response.body)
