import sqlalchemy as SA
import tornado.web

import pushmanager.core.db as db
from pushmanager.core.requesthandler import RequestHandler

class SmartDestServlet(RequestHandler):

    @tornado.web.authenticated
    def get(self):
        query = db.push_pushes.select(SA.and_(
                        db.push_pushes.c.state == 'accepting',
                        SA.exists([1],
                            SA.and_(
                                db.push_pushcontents.c.push == db.push_pushes.c.id,
                                db.push_pushcontents.c.request == db.push_requests.c.id,
                                db.push_requests.c.user == self.current_user,
                            ),
                        ),
                    ),
                    order_by=db.push_pushes.c.created.asc(),
                )
        db.execute_cb(query, self.on_db_response)

    def on_db_response(self, success, db_results):
        self.check_db_results(success, db_results)

        if db_results and db_results.rowcount > 0:
            push = db_results.first()
            if push:
                return self.redirect('/push?id=%s' % push['id'])

        return self.redirect('/pushes')
