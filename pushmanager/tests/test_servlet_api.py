import json
import time

import testify as T
from pushmanager.core.util import get_servlet_urlspec
from pushmanager.servlets.api import APIServlet
from pushmanager.testing.testdb import FakeDataMixin
from pushmanager.testing.testservlet import ServletTestMixin


class APITests(T.TestCase, ServletTestMixin, FakeDataMixin):

    def get_handlers(self):
        return [get_servlet_urlspec(APIServlet)]

    def api_call(self, req):
        response = self.fetch("/api/%s" % req)
        assert response.error is None
        return json.loads(response.body)

    def test_userlist(self):
        results = self.api_call("userlist")
        T.assert_equal(results, ['bmetin', "otheruser"])

    def test_request(self):
        results = self.api_call("request?id=1")
        T.assert_equal(results['title'], "Fix stuff")

    def test_push(self):
        results = self.api_call("push?id=1")
        T.assert_equal(results['pushtype'], "regular")

    def test_pushdata(self):
        push_info, contents, requests = self.api_call("pushdata?id=1")
        T.assert_equal(push_info['title'], "Test Push")
        T.assert_length(contents, 2)
        T.assert_equal(requests[0]['state'], "requested")

    def test_pushes(self):
        pushes, last_push = self.api_call("pushes")
        T.assert_length(pushes, 2)
        T.assert_equal(last_push, 2)

        pushes, last_push = self.api_call("pushes?rpp=1")
        T.assert_length(pushes, 1)

        pushes, last_push = self.api_call("pushes?offset=1")
        T.assert_length(pushes, 1)

    def test_pushes_order(self):
        self.insert_pushes()
        pushes, _ = self.api_call("pushes")
        T.assert_length(pushes, 6)

        lastpush = None
        for push in pushes:
            if lastpush is not None:
                if push['state'] == 'accepting':
                    T.assert_equal('accepting', lastpush['state'])
                elif lastpush['state'] != 'accepting':
                    T.assert_gte(push['modified'], lastpush['modified'])
            lastpush = push

    def test_pushes_state_filter(self):
        self.insert_pushes()
        pushes, last_push = self.api_call("pushes?state=live")
        T.assert_length(pushes, 1)
        for push in pushes:
            T.assert_equal(push['state'], 'live')

    def test_pushcontents(self):
        pushcontents = self.api_call("pushcontents?id=1")
        T.assert_length(pushcontents, 1)
        T.assert_equal(pushcontents[0]['state'], 'pickme')

    def test_pushbyrequest(self):
        push = self.api_call("pushbyrequest?id=1")
        T.assert_equal(push['title'], "Test Push")

    def test_pushitems(self):
        pushitems = self.api_call("pushitems?push_id=1")
        T.assert_length(pushitems, 0)

    def test_requestsearch(self):
        requests = self.api_call("requestsearch?mbefore=%d" % time.time())
        T.assert_length(requests, 3)

        requests = self.api_call("requestsearch?cbefore=%d" % time.time())
        T.assert_length(requests, 3)

        requests = self.api_call("requestsearch?state=requested")
        T.assert_length(requests, 2)

        requests = self.api_call("requestsearch?state=pickme")
        T.assert_length(requests, 1)

        requests = self.api_call("requestsearch?user=bmetin")
        T.assert_length(requests, 2)

        requests = self.api_call("requestsearch?repo=bmetin")
        T.assert_length(requests, 2)

        requests = self.api_call("requestsearch?branch=bmetin_fix_stuff")
        T.assert_length(requests, 1)

        requests = self.api_call("requestsearch?title=fix")
        T.assert_length(requests, 2)

        requests = self.api_call("requestsearch?title=fix&limit=1")
        T.assert_length(requests, 1)

    def test_requestsearch_when_user_and_repo_are_different(self):
        requests = self.api_call("requestsearch?user=otheruser&repo=testuser&branch=testuser_important_fixes")
        T.assert_length(requests, 1)
