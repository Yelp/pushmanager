import core.db as db
from core.mail import MailQueue
from core.requesthandler import RequestHandler
from core.settings import Settings
import core.util
from core.xmppclient import XMPPQueue

class AddRequestServlet(RequestHandler):

    def post(self):
        if not self.current_user:
            return self.send_error(403)
        self.pushid = core.util.get_int_arg(self.request, 'push')
        self.request_ids = self.request.arguments.get('request', [])

        insert_queries = []
        for i in self.request_ids:
            if Settings["db_uri"].startswith("sqlite"):
                query = db.push_pushcontents.insert({'request':int(i), 'push':self.pushid}).prefix_with('OR IGNORE')
            else:
                query = db.push_pushcontents.insert({'request':int(i), 'push':self.pushid}).prefix_with('IGNORE')
            insert_queries.append(query)
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
            msg = (
                """
                <p>
                    %(pushmaster)s has accepted your request into a push:
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
            msg = '%(pushmaster)s has accepted your request "%(title)s" into a push:\nhttps://%(pushmanager_servername)s/push?id=%(pushid)s' % {
                'pushmanager_servername': Settings['main_app']['servername'],
                'pushmaster': self.current_user,
                'title': req['title'],
                'pushid': self.pushid,
            }
            XMPPQueue.enqueue_user_xmpp([req['user']], msg)
