import sqlalchemy as SA
import tornado.web

import core.db as db
from core.requesthandler import RequestHandler
import core.util

class UndelayRequestServlet(RequestHandler):

    @tornado.web.asynchronous
    def post(self):
        if not self.current_user:
            return self.send_error(403)
        self.requestid = core.util.get_int_arg(self.request, 'id')
        update_query = db.push_requests.update().where(SA.and_(
            db.push_requests.c.id == self.requestid,
            db.push_requests.c.user == self.current_user,
            db.push_requests.c.state == 'delayed',
        )).values({
            'state': 'requested',
        })
        select_query = db.push_requests.select().where(
            db.push_requests.c.id == self.requestid,
        )
        db.execute_transaction_cb([update_query, select_query], self.on_db_complete)

    # allow both GET and POST
    get = post

    def on_db_complete(self, success, db_results):
        self.check_db_results(success, db_results)

        self.redirect("/requests?user=%s" % self.current_user)
