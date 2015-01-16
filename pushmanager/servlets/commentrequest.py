import sqlalchemy as SA

import pushmanager.core.db as db
import pushmanager.core.util
from pushmanager.core.mail import MailQueue
from pushmanager.core.requesthandler import RequestHandler
from pushmanager.core.xmppclient import XMPPQueue
from tornado.escape import xhtml_escape


class CommentRequestServlet(RequestHandler):

    def post(self):
        if not self.current_user:
            return self.send_error(403)

        requestid = pushmanager.core.util.get_int_arg(self.request, 'id')
        comment = pushmanager.core.util.get_str_arg(self.request, 'comment')
        self.comment = comment
        if not comment:
            return self.send_error(500)

        update_query = db.push_requests.update().where(
            db.push_requests.c.id == requestid,
        ).values({
            'comments': SA.func.concat(
                db.push_requests.c.comments,
                '\n\n---\n\nComment from %s:\n\n' % self.current_user,
                comment,
            ),
        })
        select_query = db.push_requests.select().where(
            db.push_requests.c.id == requestid,
        )
        db.execute_transaction_cb([update_query, select_query], self.on_db_complete)

    get = post

    def on_db_complete(self, success, db_results):
        self.check_db_results(success, db_results)

        if db_results:
            req = db_results[1].first()
            msg = (
                """
                <p>
                    %(pushmaster)s has commented on your request:
                </p>
                <p>
                    <strong>%(user)s - %(title)s</strong><br />
                    <em>%(repo)s/%(branch)s</em>
                </p>
                <pre>
%(comment)s
                </pre>
                <p>
                    Regards,<br />
                    PushManager
                </p>"""
            ) % pushmanager.core.util.EscapedDict({
                    'pushmaster': self.current_user,
                    'user': req['user'],
                    'title': req['title'],
                    'repo': req['repo'],
                    'branch': req['branch'],
                    'comment': self.comment,
                })
            subject = "[push comment] %s - %s" % (req['user'], req['title'])
            MailQueue.enqueue_user_email([req['user']], msg, subject)
            msg = '%(pushmaster)s has commented on your request "%(title)s":\n%(comment)s' % {
                    'pushmaster': self.current_user,
                    'title': req['title'],
                    'comment': self.comment,
                }
            XMPPQueue.enqueue_user_xmpp([req['user']], msg)
            newcomments = req[db.push_requests.c.comments]
            self.write(xhtml_escape(newcomments))
