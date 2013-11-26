import sqlalchemy as SA

import pushmanager.core.db as db
from pushmanager.core.settings import Settings
from pushmanager.core.mail import MailQueue
from pushmanager.core.requesthandler import RequestHandler
import pushmanager.core.util
from pushmanager.core.xmppclient import XMPPQueue

class DeployPushServlet(RequestHandler):

    def _arg(self, key):
        return pushmanager.core.util.get_str_arg(self.request, key, '')

    def post(self):
        if not self.current_user:
            return self.send_error(403)
        self.pushid = pushmanager.core.util.get_int_arg(self.request, 'id')
        request_query = db.push_requests.update().where(
            SA.and_(db.push_requests.c.state == 'added',
                SA.exists([1],
                    SA.and_(
                        db.push_pushcontents.c.push == self.pushid,
                        db.push_pushcontents.c.request == db.push_requests.c.id,
                    )
                )
            )).values({
                'state': 'staged',
            })
        staged_query = db.push_requests.select().where(
            SA.and_(db.push_requests.c.state == 'staged',
                    db.push_pushcontents.c.push == self.pushid,
                    db.push_pushcontents.c.request == db.push_requests.c.id,
            ))
        push_query = db.push_pushes.select().where(
                db.push_pushes.c.id == self.pushid,
            )
        db.execute_transaction_cb([request_query, staged_query, push_query], self.on_db_complete)

    def on_db_complete(self, success, db_results):
        self.check_db_results(success, db_results)

        _, staged_requests, push_result = db_results
        push = push_result.fetchone()

        for req in staged_requests:
            if req['watchers']:
                user_string = '%s (%s)' % (req['user'], req['watchers'])
                users = [req['user']] + req['watchers'].split(',')
            else:
                user_string = req['user']
                users = [req['user']]
            msg = (
                """
                <p>
                    %(pushmaster)s has deployed request for %(user)s to %(pushstage)s:
                </p>
                <p>
                    <strong>%(user)s - %(title)s</strong><br />
                    <em>%(repo)s/%(branch)s</em>
                </p>
                <p>
                    Once you've checked that it works, mark it as verified here:
                    <a href="https://%(pushmanager_servername)s/push?id=%(pushid)s">
                        https://%(pushmanager_servername)s/push?id=%(pushid)s
                    </a>
                </p>
                <p>
                    Regards,<br />
                    PushManager
                </p>"""
                ) % pushmanager.core.util.EscapedDict({
                    'pushmaster': self.current_user,
                    'pushmanager_servername': Settings['main_app']['servername'],
                    'user': user_string,
                    'title': req['title'],
                    'repo': req['repo'],
                    'branch': req['branch'],
                    'pushid': self.pushid,
                    'pushstage': push['stageenv'],
                })
            subject = "[push] %s - %s" % (user_string, req['title'])
            MailQueue.enqueue_user_email(users, msg, subject)

            msg = '%(pushmaster)s has deployed request "%(title)s" for %(user)s to stage.\nPlease verify it at https://%(pushmanager_servername)s/push?id=%(pushid)s' % {
                    'pushmaster': self.current_user,
                    'pushmanager_servername': Settings['main_app']['servername'],
                    'title': req['title'],
                    'pushid': self.pushid,
                    'user': user_string,
                }
            XMPPQueue.enqueue_user_xmpp(users, msg)

        if push['extra_pings']:
            for user in push['extra_pings'].split(','):
                XMPPQueue.enqueue_user_xmpp([user], '%s has deployed a push to stage.' % self.current_user)
