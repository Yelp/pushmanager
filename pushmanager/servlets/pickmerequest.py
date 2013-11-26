import sqlalchemy as SA

import core.db as db
from core.requesthandler import RequestHandler
import core.util

class PickMeRequestServlet(RequestHandler):

    def post(self):
        if not self.current_user:
            return self.send_error(403)

        self.pushid = core.util.get_int_arg(self.request, 'push')
        self.request_ids = self.request.arguments.get('request', [])

        db.execute_cb(db.push_pushes.select().where(db.push_pushes.c.id == self.pushid), self.on_push_select)

    def on_push_select(self, success, db_results):
        if not success or not db_results:
            return self.send_error(500)

        pushrow = db_results.fetchone()
        if not pushrow:
            return self.send_error(500)

        if pushrow[db.push_pushes.c.state] != 'accepting':
            return self.send_error(403)

        insert_queries = [db.push_pushcontents.insert({'request': int(i), 'push': self.pushid}) for i in self.request_ids]
        update_query = db.push_requests.update().where(SA.and_(
                db.push_requests.c.id.in_(self.request_ids),
                db.push_requests.c.state == 'requested',
            )).values({'state':'pickme'})
        request_query = db.push_requests.select().where(
            db.push_requests.c.id.in_(self.request_ids))

        condition_query = SA.select(
            [db.push_pushes, db.push_pushcontents],
            SA.and_(
                db.push_pushcontents.c.request.in_(self.request_ids),
                db.push_pushes.c.id == db.push_pushcontents.c.push,
                db.push_pushes.c.state != 'discarded'
            )
        )

        def condition_fn(db_results):
            return db_results.fetchall() == []

        db.execute_transaction_cb(
            insert_queries + [update_query, request_query],
            self.on_db_complete,
            condition = (condition_query, condition_fn)
        )

    # allow both GET and POST
    get = post

    def on_db_complete(self, success, db_results):
        self.check_db_results(success, db_results)

class UnpickMeRequestServlet(RequestHandler):

    def post(self):
        if not self.current_user:
            return self.send_error(403)

        self.pushid = core.util.get_int_arg(self.request, 'push')
        self.request_id = self.request.arguments.get('request', [None])[0]
        delete_query = db.push_pushcontents.delete().where(
            SA.exists([1], SA.and_(
                db.push_pushcontents.c.request == self.request_id,
                db.push_pushcontents.c.push == self.pushid,
                db.push_requests.c.id == db.push_pushcontents.c.request,
                db.push_requests.c.state == 'pickme',
            )))
        update_query = db.push_requests.update().where(SA.and_(
                db.push_requests.c.id == self.request_id,
                db.push_requests.c.state == 'pickme',
            )).values({'state':'requested'})

        db.execute_transaction_cb([delete_query, update_query], self.on_db_complete)

    # allow both GET and POST
    get = post

    def on_db_complete(self, success, db_results):
        self.check_db_results(success, db_results)
