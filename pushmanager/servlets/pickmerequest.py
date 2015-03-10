import sqlalchemy as SA
import json

import pushmanager.core.db as db
import pushmanager.core.util
from pushmanager.core.git import GitQueue
from pushmanager.core.git import GitTaskAction
from pushmanager.core.util import query_reviewboard
from pushmanager.core.util import does_review_sha_match_head_of_branch
from pushmanager.core.util import has_shipit
from pushmanager.core.util import check_tag
from pushmanager.core.requesthandler import RequestHandler

from pushmanager.core.settings import Settings


class PickMeRequestServlet(RequestHandler):

    def post(self):
        if not self.current_user:
            return self.send_error(403)

        self.pushid = pushmanager.core.util.get_int_arg(self.request, 'push')
        self.request_ids = self.request.arguments.get('request', [])

        request_query = db.push_requests.select().where(db.push_requests.c.id.in_(self.request_ids))
        db.execute_cb(request_query, self.validate_pickme_requests)

    def validate_pickme_requests(self, success, db_results):
        if not success or not db_results:
            return self.send_error(500)

        request_row = db_results.fetchone()
        if not request_row:
            return self.send_error(500)

        reviewboard_stats = query_reviewboard(
            request_row[db.push_requests.c.reviewid],
            Settings['reviewboard']['servername'],
            Settings['reviewboard']['username'],
            Settings['reviewboard']['password']
        )

        head_sha = request_row[db.push_requests.c.revision]
        match, match_msg = does_review_sha_match_head_of_branch(reviewboard_stats, head_sha)
        is_shiped, shipit_msg = has_shipit(reviewboard_stats)
        has_test_tag, test_msg = check_tag(request_row[db.push_requests.c.tags], [Settings['tests_tag']['tag']])

        is_request_valid = match and is_shiped and has_test_tag
        msg = '\n'.join([match_msg, shipit_msg, test_msg])

        self.write(json.dumps({
            'valid': is_request_valid,
            'msg': msg
        }))

        if is_request_valid:
            db.execute_cb(db.push_pushes.select().where(db.push_pushes.c.id == self.pushid), self.on_push_select)

    def on_push_select(self, success, db_results):
        if not success or not db_results:
            return self.send_error(500)

        pushrow = db_results.fetchone()
        if not pushrow:
            return self.send_error(500)

        if pushrow[db.push_pushes.c.state] != 'accepting':
            return self.send_error(403)

        insert_queries = [
            db.push_pushcontents.insert({
                'request': int(i),
                'push': self.pushid
            }) for i in self.request_ids
        ]
        update_query = db.push_requests.update().where(SA.and_(
                db.push_requests.c.id.in_(self.request_ids),
                db.push_requests.c.state == 'requested',
            )).values({'state': 'pickme'})
        request_query = db.push_requests.select().where(
            db.push_requests.c.id.in_(self.request_ids))

        condition_query = SA.select(
            [db.push_pushes, db.push_pushcontents],
            SA.and_(
                db.push_pushcontents.c.request.in_(self.request_ids),
                db.push_pushes.c.id == db.push_pushcontents.c.push,
                db.push_pushes.c.state != 'discarded'
            )
        )

        def condition_fn(db_results):
            return db_results.fetchall() == []

        db.execute_transaction_cb(
            insert_queries + [update_query, request_query],
            self.on_db_complete,
            condition=(condition_query, condition_fn)
        )

    # allow both GET and POST
    get = post

    def on_db_complete(self, success, db_results):
        self.check_db_results(success, db_results)
        for request_id in self.request_ids:
            GitQueue.enqueue_request(
                GitTaskAction.TEST_PICKME_CONFLICT,
                request_id,
                pushmanager_url=self.get_base_url()
            )


class UnpickMeRequestServlet(RequestHandler):

    def post(self):
        if not self.current_user:
            return self.send_error(403)

        self.pushid = pushmanager.core.util.get_int_arg(self.request, 'push')
        self.request_id = self.request.arguments.get('request', [None])[0]
        delete_query = db.push_pushcontents.delete().where(
            SA.exists([1], SA.and_(
                db.push_pushcontents.c.request == self.request_id,
                db.push_pushcontents.c.push == self.pushid,
                db.push_requests.c.id == db.push_pushcontents.c.request,
                db.push_requests.c.state == 'pickme',
            )))
        update_query = db.push_requests.update().where(SA.and_(
                db.push_requests.c.id == self.request_id,
                db.push_requests.c.state == 'pickme',
            )).values({'state': 'requested'})

        db.execute_transaction_cb([delete_query, update_query], self.on_db_complete)

    # allow both GET and POST
    get = post

    def on_db_complete(self, success, db_results):
        self.check_db_results(success, db_results)
        # Re-check pickmes that are marked as conflicting, in case this was the pickme
        # that they conflicted against.
        GitQueue.enqueue_request(
            GitTaskAction.TEST_CONFLICTING_PICKMES,
            self.pushid,
            pushmanager_url=self.get_base_url()
        )
