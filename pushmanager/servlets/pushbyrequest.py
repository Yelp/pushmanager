import tornado.gen
import tornado.web

from core.requesthandler import RequestHandler
import core.util

class PushByRequestServlet(RequestHandler):

    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        requestid = core.util.get_int_arg(self.request, 'id')
        response = yield tornado.gen.Task(
                        self.async_api_call,
                        "pushbyrequest",
                        {"id": requestid}
                    )

        push = self.get_api_results(response)
        if push:
            self.redirect('/push?id=%s' % push['id'])
