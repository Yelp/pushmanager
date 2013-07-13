import time

import core.db as db
from core.requesthandler import RequestHandler
import core.util

class EditPushServlet(RequestHandler):

    def _arg(self, key):
        return core.util.get_str_arg(self.request, key, '')

    def post(self):
        if not self.current_user:
            return self.send_error(403)
        self.pushid = core.util.get_int_arg(self.request, 'id')
        query = db.push_pushes.update().where(db.push_pushes.c.id == self.pushid).values(**{
            'title': self._arg('push-title'),
            'user': self.current_user,
            'branch': self._arg('push-branch'),
            'revision': "0"*40,
            'stageenv': self._arg('push-stageenv'),
            'modified': time.time(),
            })
        db.execute_cb(
            query,
            lambda _, __: self.redirect("/push?id=%d" % self.pushid)
        )
