import pushmanager.core.db as db
import pushmanager.core.util
from pushmanager.core.db import InsertIgnore
from pushmanager.core.mail import MailQueue
from pushmanager.core.requesthandler import RequestHandler
from pushmanager.core.settings import Settings
from pushmanager.core.xmppclient import XMPPQueue


class AddRequestServlet(RequestHandler):

    def post(self):
        if not self.current_user:
            return self.send_error(403)
        self.pushid = pushmanager.core.util.get_int_arg(self.request, 'push')
        self.request_ids = self.request.arguments.get('request', [])

        insert_queries = [
                InsertIgnore(db.push_pushcontents, ({'request': int(i), 'push': self.pushid}))
                for i in self.request_ids
        ]
        update_query = db.push_requests.update().where(
            db.push_requests.c.id.in_(self.request_ids)).values({'state':'added'})
        request_query = db.push_requests.select().where(
            db.push_requests.c.id.in_(self.request_ids))

        db.execute_transaction_cb(insert_queries + [update_query, request_query], self.on_db_complete)

    # allow both GET and POST
    get = post

    def on_db_complete(self, success, db_results):
        self.check_db_results(success, db_results)

        for req in db_results[-1]:
            if req['watchers']:
                user_string = '%s (%s)' % (req['user'], req['watchers'])
                users = [req['user']] + req['watchers'].split(',')
            else:
                user_string = req['user']
                users = [req['user']]
            msg = (
                """
                <p>
                    %(pushmaster)s has accepted request for %(user)s into a push:
                </p>
                <p>
                    <strong>%(user)s - %(title)s</strong><br />
                    <em>%(repo)s/%(branch)s</em>
                </p>
                <p>
                    Regards,<br />
                    PushManager
                </p>"""
                ) % pushmanager.core.util.EscapedDict({
                    'pushmaster': self.current_user,
                    'user': user_string,
                    'title': req['title'],
                    'repo': req['repo'],
                    'branch': req['branch'],
                })
            subject = "[push] %s - %s" % (user_string, req['title'])
            MailQueue.enqueue_user_email(users, msg, subject)
            msg = '%(pushmaster)s has accepted request "%(title)s" for %(user)s into a push:\n%(pushmanager_base_url)s/push?id=%(pushid)s' % {
                'pushmanager_base_url' : self.get_base_url(),
                'pushmaster': self.current_user,
                'title': req['title'],
                'pushid': self.pushid,
                'user': user_string,
            }
            XMPPQueue.enqueue_user_xmpp(users, msg)
