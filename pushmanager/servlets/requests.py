import pushmanager.core.util
import tornado.gen
import tornado.web
from pushmanager.core.requesthandler import RequestHandler


class RequestsServlet(RequestHandler):

    @tornado.web.asynchronous
    @tornado.web.authenticated
    @tornado.gen.engine
    def get(self):
        username = pushmanager.core.util.get_str_arg(self.request, 'user')
        limit_count = pushmanager.core.util.get_int_arg(self.request, 'max')
        arguments = {'limit' : limit_count}

        if username:
            arguments['user'] = username
            page_title = 'Requests from %s' % username
            show_count = False
        else:
            arguments['limit'] = 0
            arguments['state'] = 'requested'
            page_title = 'Open Requests'
            show_count = True

        response = yield tornado.gen.Task(
                        self.async_api_call,
                        "requestsearch",
                        arguments
                    )

        requests = self.get_api_results(response)
        self.render("requests.html", requests=requests, page_title=page_title, show_count=show_count)
