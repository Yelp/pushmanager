import sqlalchemy as SA

import pushmanager.core.db as db
import pushmanager.core.util
from pushmanager.core.requesthandler import RequestHandler
from pushmanager.core.settings import Settings
from pushmanager.core.xmppclient import XMPPQueue


class VerifyRequestServlet(RequestHandler):

    def _arg(self, key):
        return pushmanager.core.util.get_str_arg(self.request, key, '')

    def post(self):
        if not self.current_user:
            return self.send_error(403)
        self.requestid = pushmanager.core.util.get_int_arg(self.request, 'id')
        self.pushid = pushmanager.core.util.get_int_arg(self.request, 'push')
        select_query = db.push_pushes.select().where(
            db.push_pushes.c.id == self.pushid,
        )
        update_query = db.push_requests.update().where(SA.and_(
            db.push_requests.c.state == 'staged',
            db.push_requests.c.id == self.requestid,
            SA.exists([1],
                SA.and_(
                    db.push_pushcontents.c.push == self.pushid,
                    db.push_pushcontents.c.request == self.requestid,
                )
            ))).values({
                'state': 'verified',
            })
        finished_query = db.push_requests.select().where(SA.and_(
            db.push_requests.c.state == 'staged',
            SA.exists([1],
                SA.and_(
                    db.push_pushcontents.c.push == self.pushid,
                    db.push_pushcontents.c.request == db.push_requests.c.id,
                )
            )))
        db.execute_transaction_cb([select_query, update_query, finished_query], self.on_db_complete)

    def on_db_complete(self, success, db_results):
        self.check_db_results(success, db_results)

        push = db_results[0].first()
        unfinished_requests = db_results[2].first()
        pushmanager_base_url = self.get_base_url()
        if not unfinished_requests:
            msg = "All currently staged requests in %s/push?id=%s have been marked as verified." % \
                (pushmanager_base_url, self.pushid)
            XMPPQueue.enqueue_user_xmpp([push['user']], msg)
