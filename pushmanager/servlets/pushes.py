import tornado.gen
import tornado.web

from pushmanager.core.requesthandler import RequestHandler
import pushmanager.core.util

class PushesServlet(RequestHandler):

    @tornado.web.authenticated
    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        pushes_per_page = pushmanager.core.util.get_int_arg(self.request, 'rpp', 50)
        before = pushmanager.core.util.get_int_arg(self.request, 'before', 0)
        response = yield tornado.gen.Task(
                        self.async_api_call,
                        "pushes",
                        {"rpp": pushes_per_page, "before": before}
                    )

        results = self.get_api_results(response)
        if not results:
            self.finish()

        pushes, last_push = results
        self.render(
            "pushes.html",
            page_title="Pushes",
            pushes=pushes,
            rpp=pushes_per_page,
            last_push=last_push
        )
