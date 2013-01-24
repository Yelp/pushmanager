import tornado.gen
import tornado.web

from core.requesthandler import RequestHandler
import core.util

class RequestServlet(RequestHandler):

    @tornado.web.asynchronous
    @tornado.web.authenticated
    @tornado.gen.engine
    def get(self):
        request_id = core.util.get_int_arg(self.request, 'id')
        if not request_id:
            self.send_error(404)

        response = yield tornado.gen.Task(
                        self.async_api_call,
                        "request",
                        {'id': request_id}
                    )

        req = self.get_api_results(response)
        if not req:
            self.send_error()

        self.render("request.html", page_title="Request #%d" % request_id, req=req)
