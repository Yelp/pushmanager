import time

import pushmanager.core.db as db
from pushmanager.core.requesthandler import RequestHandler
import pushmanager.core.util

class EditPushServlet(RequestHandler):

    def _arg(self, key):
        return pushmanager.core.util.get_str_arg(self.request, key, '')

    def post(self):
        if not self.current_user:
            return self.send_error(403)
        self.pushid = pushmanager.core.util.get_int_arg(self.request, 'id')
        query = db.push_pushes.update().where(db.push_pushes.c.id == self.pushid).values(**{
            'title': self._arg('push-title'),
            'user': self.current_user,
            'branch': self._arg('push-branch'),
            'stageenv': self._arg('push-stageenv'),
            'revision': "0"*40,
            'modified': time.time(),
            })
        db.execute_cb(
            query,
            lambda _, __: self.redirect("/push?id=%d" % self.pushid)
        )
