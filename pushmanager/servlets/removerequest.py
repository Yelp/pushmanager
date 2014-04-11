import sqlalchemy as SA
import time
import tornado.web

import core.db as db
from core.mail import MailQueue
from core.requesthandler import RequestHandler
import core.util
from core.xmppclient import XMPPQueue

class RemoveRequestServlet(RequestHandler):

    @tornado.web.asynchronous
    def post(self):
        if not self.current_user:
            return self.send_error(403)
        self.pushid = core.util.get_int_arg(self.request, 'push')
        self.requestid = self.request.arguments.get('request', [])
        select_query = db.push_requests.select().where(
            db.push_requests.c.id.in_(self.requestid)
        )
        update_query = db.push_requests.update().where(SA.and_(
            db.push_requests.c.id.in_(self.requestid),
            SA.exists([1], SA.and_(
                db.push_pushcontents.c.push == self.pushid,
                db.push_pushcontents.c.request == db.push_requests.c.id,
            )),
        )).values({'state':'requested'})
        delete_query = db.push_pushcontents.delete(SA.and_(
            db.push_pushcontents.c.push == self.pushid,
            db.push_pushcontents.c.request.in_(self.requestid),
        ))
        db.execute_transaction_cb([select_query, update_query, delete_query], self.on_db_complete)

    # allow both GET and POST
    get = post

    def on_db_complete(self, success, db_results):
        self.check_db_results(success, db_results)

        reqs, _, _ = db_results
        removal_dicts = []
        for req in reqs:
            if req['watchers']:
                user_string = '%s (%s)' % (req['user'], req['watchers'])
                users = [req['user']] + req['watchers'].split(',')
            else:
                user_string = req['user']
                users = [req['user']]
            msg = (
                """
                <p>
                    %(pushmaster)s has removed request for %(user)s from a push:
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
            msg = '%(pushmaster)s has removed request "%(title)s" for %(user)s from a push' % {
                    'pushmaster': self.current_user,
                    'title': req['title'],
                    'pushid': self.pushid,
                    'user': user_string,
                }
            XMPPQueue.enqueue_user_xmpp(users, msg)
            removal_dicts.append({
                'request': req['id'],
                'push': self.pushid,
                'reason': 'removal after %s' % req['state'],
                'pushmaster': self._current_user,
                'timestamp': int(time.time()),
            })

        removal_queries = [db.push_removals.insert(removal) for removal in removal_dicts]
        db.execute_transaction_cb(removal_queries, self.on_db_insert_complete)

    def on_db_insert_complete(self, success, db_results):
        if not success:
            self.send_error(500)
        self.finish()
