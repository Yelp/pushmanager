import sqlalchemy as SA
import time

import core.db as db
from core.mail import MailQueue
from core.rb import RBQueue
from core.requesthandler import RequestHandler
import core.util

class LivePushServlet(RequestHandler):

    def _arg(self, key):
        return core.util.get_str_arg(self.request, key, '')

    def post(self):
        if not self.current_user:
            return self.send_error(403)
        self.pushid = core.util.get_int_arg(self.request, 'id')
        push_query = db.push_pushes.update().where(db.push_pushes.c.id == self.pushid).values({
            'state': 'live',
            'modified': time.time(),
            })
        request_query = db.push_requests.update().where(SA.and_(
            db.push_requests.c.state == 'blessed',
            SA.exists([1],
                SA.and_(
                    db.push_pushcontents.c.push == self.pushid,
                    db.push_pushcontents.c.request == db.push_requests.c.id,
                )
            ))).values({
                'state': 'live',
                'modified': time.time(),
            })
        reset_query = db.push_requests.update().where(
            SA.exists([1],
                SA.and_(
                    db.push_requests.c.state == 'pickme',
                    db.push_pushcontents.c.push == self.pushid,
                    db.push_pushcontents.c.request == db.push_requests.c.id,
                )
            )).values({
                'state': 'requested',
            })
        delete_query = db.push_pushcontents.delete().where(
            SA.exists([1], SA.and_(
                db.push_pushcontents.c.push == self.pushid,
                db.push_pushcontents.c.request == db.push_requests.c.id,
                db.push_requests.c.state == 'requested',
            )))
        live_query = db.push_requests.select().where(
            SA.and_(db.push_requests.c.state == 'live',
                    db.push_pushcontents.c.push == self.pushid,
                    db.push_pushcontents.c.request == db.push_requests.c.id,
            ))
        db.execute_transaction_cb([push_query, request_query, reset_query, delete_query, live_query], self.on_db_complete)

    def on_db_complete(self, success, db_results):
        self.check_db_results(success, db_results)

        _, _, _, _, live_requests = db_results
        for req in live_requests:
            if req['reviewid']:
                review_id = int(req['reviewid'])
                RBQueue.enqueue_review(review_id)

            if req['watchers']:
                user_string = '%s (%s)' % (req['user'], req['watchers'])
                users = [req['user']] + req['watchers'].split(',')
            else:
                user_string = req['user']
                users = [req['user']]

            msg = (
                """
                <p>
                    %(pushmaster)s has certified request for %(user)s as stable in production:
                </p>
                <p>
                    <strong>%(user)s - %(title)s</strong><br />
                    <em>%(repo)s/%(branch)s</em>
                </p>
                <p>
                    Regards,<br />
                    PushManager
                </p>"""
                ) % core.util.EscapedDict({
                    'pushmaster': self.current_user,
                    'user': user_string,
                    'title': req['title'],
                    'repo': req['repo'],
                    'branch': req['branch'],
                })
            subject = "[push] %s - %s" % (user_string, req['title'])
            MailQueue.enqueue_user_email(users, msg, subject)
