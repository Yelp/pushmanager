import pushmanager.core.util
import tornado.gen
import tornado.web
from pushmanager.core.requesthandler import RequestHandler


class PushesServlet(RequestHandler):

    @tornado.web.authenticated
    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        pushes_per_page = pushmanager.core.util.get_int_arg(self.request, 'rpp', 50)
        offset = pushmanager.core.util.get_int_arg(self.request, 'offset', 0)
        push_user = pushmanager.core.util.get_str_arg(self.request, 'user', '')
        state = pushmanager.core.util.get_str_arg(self.request, 'state', '')
        response = yield tornado.gen.Task(
                        self.async_api_call,
                        'pushes',
                        {
                            'rpp': pushes_per_page,
                            'offset': offset,
                            'user': push_user,
                            'state': state,
                        }
                    )

        results = self.get_api_results(response)
        if not results:
            self.finish()

        pushes, pushes_count = results
        self.render(
            "pushes.html",
            page_title="Pushes",
            pushes=pushes,
            offset=offset,
            rpp=pushes_per_page,
            push_user=push_user,
            state=state,
            pushes_count=pushes_count,
        )
