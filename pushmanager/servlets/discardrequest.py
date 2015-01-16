import sqlalchemy as SA

import pushmanager.core.db as db
import pushmanager.core.util
from pushmanager.core.mail import MailQueue
from pushmanager.core.requesthandler import RequestHandler


class DiscardRequestServlet(RequestHandler):

    def post(self):
        if not self.current_user:
            return self.send_error(403)
        self.requestid = pushmanager.core.util.get_int_arg(self.request, 'id')
        update_query = db.push_requests.update().where(SA.and_(
            db.push_requests.c.id == self.requestid,
            db.push_requests.c.user == self.current_user,
            db.push_requests.c.state.in_(['requested', 'delayed']),
        )).values({
            'state': 'discarded',
        })
        select_query = db.push_requests.select().where(
            db.push_requests.c.id == self.requestid,
        )
        db.execute_transaction_cb([update_query, select_query], self.on_db_complete)
    # allow both GET and POST
    get = post

    def on_db_complete(self, success, db_results):
        self.check_db_results(success, db_results)

        _, req = db_results
        req = req.first()
        if req['state'] != 'discarded':
            # We didn't actually discard the record, for whatever reason
            return self.redirect("/requests?user=%s" % self.current_user)

        if req['watchers']:
            user_string = '%s (%s)' % (req['user'], req['watchers'])
            users = [req['user']] + req['watchers'].split(',')
        else:
            user_string = req['user']
            users = [req['user']]
        msg = (
            """
            <p>
                Request for %(user)s has been discarded:
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

        self.redirect("/requests?user=%s" % self.current_user)
