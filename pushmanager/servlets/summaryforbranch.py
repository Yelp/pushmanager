import operator

import pushmanager.core.util
import tornado.gen
import tornado.web
from pushmanager.core.requesthandler import RequestHandler
from pushmanager.core.settings import Settings


class SummaryForBranchServlet(RequestHandler):

    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        userbranch = pushmanager.core.util.get_str_arg(self.request, 'userbranch')
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
