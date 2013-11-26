# -*- coding: utf-8 -*-
from contextlib import nested
import mock
import urllib

from core import db
from core.util import get_servlet_urlspec
from servlets.checklist import checklist_reminders
from servlets.newrequest import NewRequestServlet
import testing as T

class NewRequestServletTest(T.TestCase, T.ServletTestMixin, T.FakeDataMixin):

    basic_request = {
           'request-title': 'Test Push Request Title',
           'request-tags': 'super-safe,logs',
           'request-review': 1,
           'request-repo': 'testuser',
           'request-branch': 'super_safe_fix',
           'request-comments': 'No comment',
           'request-description': 'I approve this fix!',
           'request-watchers': 'testuser2,testuser3',
           'request-takeover': '',
    }

    @T.class_setup_teardown
    def mock(self):
        with nested(
            mock.patch.dict(db.Settings, T.MockedSettings),
            mock.patch.object(NewRequestServlet, "redirect"),
            mock.patch.object(
                NewRequestServlet,
                "get_current_user",
                return_value="testuser"
            )
        ):
            yield

    def get_handlers(self):
        return [get_servlet_urlspec(NewRequestServlet)]

    def assert_submit_request(self, request, edit=False, redirect=None):
        results = []

        def on_db_return(success, db_results):
            assert success
            results.extend(db_results.fetchall())

        results = []
        db.execute_cb(db.push_requests.select(), on_db_return)
        num_results_before = len(results)

        if redirect:
            with mock.patch.object(NewRequestServlet, "redirect") as redir:
                response = self.fetch(
                    "/newrequest",
                    method="POST",
                    body=urllib.urlencode(request)
                )
                T.assert_equal(response.error, None)

                T.assert_equal(redir.call_args[0][0], redirect)
        else:
            response = self.fetch(
                "/newrequest",
                method="POST",
                body=urllib.urlencode(request)
            )
            T.assert_equal(response.error, None)

        results = []
        db.execute_cb(db.push_requests.select(), on_db_return)
        num_results_after = len(results)

        if not edit:
            T.assert_equal(num_results_after, num_results_before + 1)

            last_req = self.get_requests()[-1]
            T.assert_equal(len(results), last_req['id'])
            return last_req
        else:
            T.assert_equal(num_results_after, num_results_before)
            last_req = self.get_requests()[-1]
            return last_req

    def assert_request(self, expected, actual):
        T.assert_equal(expected['user'], actual['user'])
        T.assert_equal(expected['request-repo'], actual['repo'])
        T.assert_equal(expected['request-branch'], actual['branch'])
        T.assert_equal(expected['request-tags'], actual['tags'])
        T.assert_equal(expected['request-comments'], actual['comments'])
        T.assert_equal(expected['request-description'], actual['description'])
        T.assert_equal(expected['request-watchers'], actual['watchers'])

    def test_newrequest(self):
        last_req = self.assert_submit_request(self.basic_request)
        basic_request = dict(self.basic_request)
        basic_request.update({'user': 'testuser'})
        self.assert_request(basic_request, last_req)

    def test_editrequest_no_takeover(self):
        last_req = self.assert_submit_request(self.basic_request)
        basic_request = dict(self.basic_request)
        basic_request.update({'user': 'testuser'})
        self.assert_request(basic_request, last_req)

        basic_request.update({'request-id': last_req['id']})
        basic_request.update({'request-user': 'testuser'})
        with mock.patch.object(
                NewRequestServlet,
                "get_current_user",
                return_value="testtakeoveruser"
                ):
            edit_req = self.assert_submit_request(basic_request, edit=True, redirect='/requests?user=testuser')
            basic_request.update({'user': 'testuser'})
            self.assert_request(basic_request, edit_req)

    def test_editrequest_takeover(self):
        last_req = self.assert_submit_request(self.basic_request)
        basic_request = dict(self.basic_request)
        basic_request.update({'user': 'testuser'})
        self.assert_request(basic_request, last_req)

        basic_request.update({'request-id': last_req['id']})
        basic_request.update({'request-takeover': 'takeover'})
        basic_request.update({'request-user': 'testuser'})
        with mock.patch.object(
                NewRequestServlet,
                "get_current_user",
                return_value="testtakeoveruser"
                ):
            edit_req = self.assert_submit_request(basic_request, edit=True, redirect='/requests?user=testtakeoveruser')
            basic_request.update({'user': 'testtakeoveruser'})
            self.assert_request(basic_request, edit_req)


class NewRequestChecklistMixin(T.ServletTestMixin, T.FakeDataMixin):

    __test__ = False

    @T.class_setup_teardown
    def mock(self):
        with nested(
            mock.patch.dict(db.Settings, T.MockedSettings),
            mock.patch.object(NewRequestServlet, "redirect"),
            mock.patch.object(
                NewRequestServlet,
                "get_current_user",
                return_value="testuser"
            )
        ):
            yield

    def get_handlers(self):
        return [get_servlet_urlspec(NewRequestServlet)]

    def make_request_with_tags(self, tags, requestid=None):
        request = {
            'request-title': 'Test Push Request and Checklists',
            'request-tags': ','.join(tags),
            'request-review': 1,
            'request-repo': 'testuser',
            'request-branch': 'nonexistent-branch',
            'request-comments': 'No comment',
            'request-description': 'Request with tags: %s' % tags,
        }
        if requestid is not None:
            request['request-id'] = requestid

        response = self.fetch(
            '/newrequest',
            method='POST',
            body=urllib.urlencode(request)
        )
        T.assert_equal(response.error, None)

        return self.get_requests()[-1]['id']

    def get_checklists(self, requestid):
        checklists = [None]
        def on_select_return(success, db_results):
            assert success
            checklists[0] = db_results.fetchall()

        select_query = db.push_checklist.select().where(
                db.push_checklist.c.request == requestid)

        db.execute_cb(select_query, on_select_return)

        # id, *request*, *type*, complete, *target*
        simple_checklists = [(cl[1], cl[2], cl[4]) for cl in checklists[0]]
        return simple_checklists

    def assert_checklist_for_tags(self, tags, requestid=None):
        num_checks = 0
        checks = []

        # Gather reference checklists from the code
        for tag in tags:
            # While the tag name is 'search-backend', the checklist type
            # is truncated to 'search'.
            if tag == 'search-backend':
                tag = 'search'

            if tag not in checklist_reminders:
                continue

            plain_list = checklist_reminders[tag]
            num_checks += len(plain_list)
            checks += [(tag, check) for check in plain_list]

            cleanup_tag = '%s-cleanup' % tag
            cleanup_list = checklist_reminders[cleanup_tag]
            num_checks += len(cleanup_list)
            checks += [(cleanup_tag, check) for check in cleanup_list]

        reqid = self.make_request_with_tags(tags, requestid)
        checklists = self.get_checklists(reqid)

        T.assert_equal(num_checks, len(checklists))
        for check in checks:
            T.assert_in((reqid, check[0], check[1]), checklists)

        return reqid


class NewRequestChecklistTest(T.TestCase, NewRequestChecklistMixin):
    """Verify corresponding checklists with new requests"""

    def test_random_tag(self):
        tag = ['random_tag']
        self.assert_checklist_for_tags(tag)

    def test_pushplans_with_cleanup(self):
        tag = ['pushplans']
        self.assert_checklist_for_tags(tag)

    def test_search_with_cleanup(self):
        tag = ['search-backend']
        self.assert_checklist_for_tags(tag)

    def test_hoods_with_cleanup(self):
        tag = ['hoods']
        self.assert_checklist_for_tags(tag)

    def test_pushplans_search_hoods_with_cleanup(self):
        tags = ['pushplans', 'search-backend', 'hoods']
        self.assert_checklist_for_tags(tags)


class EditRequestChecklistTest(T.TestCase, NewRequestChecklistMixin):
    """Verify corresponding checklists with existing requests"""

    def test_pushplans_no_change(self):
        tag = ['pushplans']
        orig_reqid = self.assert_checklist_for_tags(tag)
        new_reqid = self.assert_checklist_for_tags(tag, orig_reqid)
        T.assert_equal(orig_reqid, new_reqid)

    def test_search_no_change(self):
        tag = ['search-backend']
        orig_reqid = self.assert_checklist_for_tags(tag)
        new_reqid = self.assert_checklist_for_tags(tag, orig_reqid)
        T.assert_equal(orig_reqid, new_reqid)

    def test_hoods_no_change(self):
        tag = ['hoods']
        orig_reqid = self.assert_checklist_for_tags(tag)
        new_reqid = self.assert_checklist_for_tags(tag, orig_reqid)
        T.assert_equal(orig_reqid, new_reqid)

    def test_pushplans_and_hoods(self):
        tag = ['hoods']
        orig_reqid = self.assert_checklist_for_tags(tag)

        tags = ['pushplans', 'hoods']
        new_reqid = self.assert_checklist_for_tags(tags, orig_reqid)

        T.assert_equal(orig_reqid, new_reqid)

    def test_search_and_hoods(self):
        tag = ['hoods']
        orig_reqid = self.assert_checklist_for_tags(tag)

        tags = ['search-backend', 'hoods']
        new_reqid = self.assert_checklist_for_tags(tags, orig_reqid)

        T.assert_equal(orig_reqid, new_reqid)

    def test_pushplans_and_search(self):
        tag = ['pushplans']
        orig_reqid = self.assert_checklist_for_tags(tag)

        tags = ['pushplans', 'search-backend']
        new_reqid = self.assert_checklist_for_tags(tags, orig_reqid)

        T.assert_equal(orig_reqid, new_reqid)

    def test_pushplans_search_and_hoods(self):
        tag = ['pushplans']
        orig_reqid = self.assert_checklist_for_tags(tag)

        tags = ['pushplans', 'search-backend']
        new_reqid = self.assert_checklist_for_tags(tags, orig_reqid)

        T.assert_equal(orig_reqid, new_reqid)

        tags = ['pushplans', 'search-backend', 'hoods']
        new_reqid = self.assert_checklist_for_tags(tags, orig_reqid)

        T.assert_equal(orig_reqid, new_reqid)


if __name__ == '__main__':
    T.run()
