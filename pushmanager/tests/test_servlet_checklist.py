from contextlib import contextmanager
from contextlib import nested
import urllib
import re

import mock

from core import db
from core.util import get_servlet_urlspec
from pushmanager.servlets.checklist import ChecklistServlet
from pushmanager.servlets.checklist import ChecklistToggleServlet
import pushmanager.testing as T

@contextmanager
def fake_checklist_request():
    with nested(
        mock.patch.dict(db.Settings, MockedSettings),
        mock.patch.object(
            ChecklistToggleServlet,
            "get_current_user",
            return_value="testuser"
        ),
        mock.patch.object(
            ChecklistServlet,
            "get_current_user",
            return_value="testuser"
        )
    ):
        yield

def on_db_return(success, db_results):
    assert success



class ChecklistServletTest(T.TestCase, ServletTestMixin, FakeDataMixin):

    def get_handlers(self):
        return [get_servlet_urlspec(ChecklistServlet)]

    def test_no_checklist(self):
        with fake_checklist_request():
            uri = "/checklist?id=1"
            response = self.fetch(uri)
            T.assert_equal(response.error, None)
            T.assert_in("No checklist items for this push", response.body)

    def test_checklist_duplicate(self):
        with fake_checklist_request():
            # insert fake data from FakeDataMixin
            fake_pushid = 2
            self.insert_pushes()
            self.insert_requests()
            test1_request = self.get_requests_by_user('testuser1')[0]
            test2_request = self.get_requests_by_user('testuser2')[0]
            self.insert_pushcontent(test1_request['id'], fake_pushid)
            self.insert_pushcontent(test2_request['id'], fake_pushid)

            # insert fake checklist data
            checklist_queries = []
            for req in (test1_request, test2_request):
                checklist_queries.append(db.push_checklist.insert({
                    'request': req['id'],
                    'type': 'search',
                    'target': 'prod'
                }))
                checklist_queries.append(db.push_checklist.insert({
                    'request': req['id'],
                    'type': 'search-cleanup',
                    'target': 'post-verify-prod'
                }))
            db.execute_transaction_cb(checklist_queries, on_db_return)

            uri = "/checklist?id=%d" % fake_pushid
            response = self.fetch(uri)
            T.assert_equal(response.error, None)
            T.assert_not_in("No checklist items for this push", response.body)
            T.assert_not_equal(re.search("for testuser\d,testuser\d", response.body), None)
            T.assert_in("After Certifying - Do In Prod", response.body)

    def test_checklist_single_search_tag(self):
        with fake_checklist_request():
            # insert fake data from FakeDataMixin
            fake_pushid = 2
            self.insert_pushes()
            self.insert_requests()
            test1_request = self.get_requests_by_user('testuser1')[0]
            self.insert_pushcontent(test1_request['id'], fake_pushid)

            # insert fake checklist data
            checklist_queries = [
                db.push_checklist.insert({
                    'request': test1_request['id'],
                    'type': 'search',
                    'target': 'prod'
                }),
                db.push_checklist.insert({
                    'request': test1_request['id'],
                    'type': 'search-cleanup',
                    'target': 'post-verify-prod'
                }),
            ]
            db.execute_transaction_cb(checklist_queries, on_db_return)

            uri = "/checklist?id=%d" % fake_pushid
            response = self.fetch(uri)
            T.assert_equal(response.error, None)
            T.assert_not_in("No checklist items for this push", response.body)
            T.assert_not_in("multiple requests", response.body)
            T.assert_in("for testuser1", response.body)
            T.assert_in("After Certifying - Do In Prod", response.body)

    def test_checklist_pushplans_tag(self):
        with fake_checklist_request():
            # insert fake data from FakeDataMixin
            fake_pushid = 2
            self.insert_pushes()
            self.insert_requests()
            test1_request = self.get_requests_by_user('testuser1')[0]
            self.insert_pushcontent(test1_request['id'], fake_pushid)

            # insert fake checklist data
            checklist_queries = [
                db.push_checklist.insert({
                    'request': test1_request['id'],
                    'type': 'pushplans',
                    'target': 'prod'
                }),
                db.push_checklist.insert({
                    'request': test1_request['id'],
                    'type': 'pushplans-cleanup',
                    'target': 'post-verify-stage'
                }),
            ]
            db.execute_transaction_cb(checklist_queries, on_db_return)

            uri = "/checklist?id=%d" % fake_pushid
            response = self.fetch(uri)
            T.assert_equal(response.error, None)
            T.assert_not_in("No checklist items for this push", response.body)
            T.assert_not_in("multiple requests", response.body)
            T.assert_in("for testuser1", response.body)
            T.assert_in("After Certifying - Do In Stage", response.body)


    def test_hoods_checklists(self):
        with fake_checklist_request():
            # insert fake data from FakeDataMixin
            fake_pushid = 2
            self.insert_pushes()
            self.insert_requests()
            req = self.get_requests_by_user('testuser1')[0]
            self.insert_pushcontent(req['id'], fake_pushid)

            # insert fake checklist data
            checklist_queries = []
            checklist_items = (
                {'request': req['id'], 'type': 'hoods', 'target': 'stage'},
                {'request': req['id'], 'type': 'hoods', 'target': 'post-stage'},
                {'request': req['id'], 'type': 'hoods', 'target': 'prod'},
                {'request': req['id'], 'type': 'hoods-cleanup', 'target': 'post-verify-stage'},
            )
            for checklist_item in checklist_items:
                checklist_queries.append(db.push_checklist.insert(checklist_item))

            db.execute_transaction_cb(checklist_queries, on_db_return)

            uri = "/checklist?id=%d" % fake_pushid
            response = self.fetch(uri)
            T.assert_equal(response.error, None)
            T.assert_not_in("No checklist items for this push", response.body)
            T.assert_in("Notify testuser1 to deploy Geoservices to stage", response.body)
            T.assert_in("Notify testuser1 to deploy Geoservices to prod", response.body)
            T.assert_in("Ask Search to force index distribution on stage for testuser1", response.body)


class ChecklistToggleServletTest(T.TestCase, ServletTestMixin, FakeDataMixin):

    def get_handlers(self):
        return [get_servlet_urlspec(ChecklistToggleServlet)]

    def test_checklist_toggle_post(self):
        complete = 0
        checklist_item = [None]

        def check_toggle(success, db_results):
            assert success
            checklist_item[0] = db_results.fetchone()
            T.assert_equal(checklist_item[0]['complete'], complete)

        with fake_checklist_request():
            # insert fake data from FakeDataMixin
            self.insert_requests()
            test_request1 = self.get_requests_by_user('testuser1')[0]
            # insert fake checklist data
            checklist_query = db.push_checklist.insert({
                'request': test_request1['id'],
                'type': 'search',
                'target': 'prod'
            })
            db.execute_cb(checklist_query, on_db_return)

            checklist_toggle_query = db.push_checklist.select(
                db.push_checklist.c.request == test_request1['id']
            )

            complete = 0
            db.execute_cb(checklist_toggle_query, check_toggle)

            complete = 1
            response = self.fetch(
                "/checklisttoggle",
                method="POST",
                body=urllib.urlencode({'id': checklist_item[0]['id'], 'complete': complete})
            )
            T.assert_equal(response.error, None)

            db.execute_cb(checklist_toggle_query, check_toggle)
