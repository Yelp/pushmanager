import pushmanager.core.util
from pushmanager.core.git import GitQueue
from pushmanager.core.git import GitTaskAction
from pushmanager.core.requesthandler import RequestHandler


class ConflictCheckServlet(RequestHandler):

    def _arg(self, key):
        return pushmanager.core.util.get_str_arg(self.request, key, '')

    def post(self):
        if not self.current_user:
            return self.send_error(403)
        self.pushid = pushmanager.core.util.get_int_arg(self.request, 'id')
        GitQueue.enqueue_request(GitTaskAction.TEST_ALL_PICKMES, self.pushid)
        self.redirect("/push?id=%d" % self.pushid)
