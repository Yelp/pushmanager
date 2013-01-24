import sqlalchemy as SA

import core.db as db
from core.mail import MailQueue
from core.requesthandler import RequestHandler
import core.util
from core.xmppclient import XMPPQueue

class BlessPushServlet(RequestHandler):

    def _arg(self, key):
        return core.util.get_str_arg(self.request, key, '')

    def post(self):
        if not self.current_user:
            return self.send_error(403)
        self.pushid = core.util.get_int_arg(self.request, 'id')
        request_query = db.push_requests.update().where(SA.and_(
            db.push_requests.c.state.in_(['staged','verified']),
            SA.exists([1],
                SA.and_(
                    db.push_pushcontents.c.push == self.pushid,
                    db.push_pushcontents.c.request == db.push_requests.c.id,
                )
            ))).values({
                'state': 'blessed',
            })
        blessed_query = db.push_requests.select().where(
            SA.and_(db.push_requests.c.state == 'blessed',
                    db.push_pushcontents.c.push == self.pushid,
                    db.push_pushcontents.c.request == db.push_requests.c.id,
            ))
        push_query = db.push_pushes.select().where(
                db.push_pushes.c.id == self.pushid,
        )
        db.execute_transaction_cb([request_query, blessed_query, push_query], self.on_db_complete)

    def on_db_complete(self, success, db_results):
        self.check_db_results(success, db_results)

        _, blessed_requests, push_results = db_results
        for req in blessed_requests:
            msg = (
                """
                <p>
                    %(pushmaster)s has deployed your request to production:
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
                    'user': req['user'],
                    'title': req['title'],
                    'repo': req['repo'],
                    'branch': req['branch'],
                })
            subject = "[push] %s - %s" % (req['user'], req['title'])
            MailQueue.enqueue_user_email([req['user']], msg, subject)
            msg = '%(pushmaster)s has deployed your request "%(title)s" to production.' % {
                    'pushmaster': self.current_user,
                    'title': req['title'],
                }
            XMPPQueue.enqueue_user_xmpp([req['user']], msg)

        push = push_results.fetchone()
        if push['extra_pings']:
            for user in push['extra_pings'].split(','):
                XMPPQueue.enqueue_user_xmpp([user], '%s has deployed a push to production.' % self.current_user)

        self.finish()
