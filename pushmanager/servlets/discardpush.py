import sqlalchemy as SA
import time

import pushmanager.core.db as db
from pushmanager.core.requesthandler import RequestHandler
import pushmanager.core.util

class DiscardPushServlet(RequestHandler):

    def _arg(self, key):
        return pushmanager.core.util.get_str_arg(self.request, key, '')

    def post(self):
        if not self.current_user:
            return self.send_error(403)
        self.pushid = pushmanager.core.util.get_int_arg(self.request, 'id')
        push_query = db.push_pushes.update().where(db.push_pushes.c.id == self.pushid).values({
            'state': 'discarded',
            'modified': time.time(),
            })
        request_query_pickme = db.push_requests.update().where(
            SA.exists([1],
                SA.and_(
                    db.push_pushcontents.c.push == self.pushid,
                    db.push_pushcontents.c.request == db.push_requests.c.id,
                    db.push_requests.c.state == 'pickme',
                )
            )).values({
                'state': 'requested',
            })
        delete_query = db.push_pushcontents.delete().where(
            SA.exists([1],
                SA.and_(
                    db.push_pushcontents.c.push == self.pushid,
                    db.push_pushcontents.c.request == db.push_requests.c.id,
                    db.push_requests.c.state == 'requested',
                )
            ))
        request_query_all = db.push_requests.update().where(
            SA.exists([1],
                SA.and_(
                    db.push_pushcontents.c.push == self.pushid,
                    db.push_pushcontents.c.request == db.push_requests.c.id,
                )
            )).values({
                'state': 'requested',
            })
        db.execute_transaction_cb([push_query, request_query_pickme, delete_query, request_query_all], self.on_db_complete)

    def on_db_complete(self, success, db_results):
        self.check_db_results(success, db_results)
