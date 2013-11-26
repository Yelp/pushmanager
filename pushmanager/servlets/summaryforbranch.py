import operator
import tornado.gen
import tornado.web

from core.requesthandler import RequestHandler
from core.settings import Settings
import core.util

class SummaryForBranchServlet(RequestHandler):

    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        userbranch = core.util.get_str_arg(self.request, 'userbranch')
        user, branch = userbranch.split('/', 1)
        response = yield tornado.gen.Task(
                        self.async_api_call,
                        "requestsearch",
                        {'repo': user, 'branch': branch}
                    )

        requests = self.get_api_results(response)

        if requests:
            req = sorted(requests, key=operator.itemgetter("id"))[0]
            self.write(req['description'] or req['title'])
            if req['reviewid']:
                self.write("\n\nReview: https://%s/r/%s" % (Settings['reviewboard']['servername'], req['reviewid']))
            self.finish()
        else:
            self.send_error(404)
