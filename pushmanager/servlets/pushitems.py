import tornado.gen
import tornado.web

from core.requesthandler import RequestHandler
import core.util

class PushItemsServlet(RequestHandler):

    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        pushid = core.util.get_int_arg(self.request, 'push', None)

        response = yield tornado.gen.Task(
                        self.async_api_call,
                        "pushitems",
                        {"push_id": pushid}
                    )

        results = self.get_api_results(response)
        self.render("pushitems.html", requests=results)
