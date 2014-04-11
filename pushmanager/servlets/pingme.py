import tornado.gen
import tornado.web

import core.db as db
from core.requesthandler import RequestHandler
import core.util

class PingMeServlet(RequestHandler):

    @tornado.web.authenticated
    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        pushid = core.util.get_int_arg(self.request, 'push')
        ping_action = core.util.get_str_arg(self.request, 'action')
        response = yield tornado.gen.Task(
                        self.async_api_call,
                        "push",
                        {"id": pushid}
                    )

        push = self.get_api_results(response)
        if not push:
            self.send_error()

        pings = set(x for x in (push['extra_pings'] or "").split(',') if x)
        if ping_action == 'set':
            pings.add(self.current_user)
        else:
            pings.discard(self.current_user)

        # This is not atomic, so we could theoretically
        # run into race conditions here, but since we're
        # working at machine speed on human input triggers
        # it should be okay for now.
        query = db.push_pushes.update().where(
            db.push_pushes.c.id == pushid,
        ).values({
            'extra_pings': ','.join(pings),
        })
        db.execute_cb(query, self.on_update_complete)

    def on_update_complete(self, success, db_results):
        self.check_db_results(success, db_results)
        self.finish()
