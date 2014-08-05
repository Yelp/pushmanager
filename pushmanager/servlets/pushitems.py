import pushmanager.core.util
import tornado.gen
import tornado.web
from pushmanager.core.requesthandler import RequestHandler


class PushItemsServlet(RequestHandler):

    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        pushid = pushmanager.core.util.get_int_arg(self.request, 'push', None)

        response = yield tornado.gen.Task(
                        self.async_api_call,
                        "pushitems",
                        {"push_id": pushid}
                    )

        results = self.get_api_results(response)
        self.render("pushitems.html", requests=results)
