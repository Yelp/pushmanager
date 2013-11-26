from collections import defaultdict
import tornado.gen
import tornado.web

from pushmanager.core.requesthandler import RequestHandler

class UserListServlet(RequestHandler):

    @tornado.web.asynchronous
    @tornado.web.authenticated
    @tornado.gen.engine
    def get(self):
        response = yield tornado.gen.Task(
                        self.async_api_call,
                        "userlist",
                        {}
                    )

        users_by_alpha = defaultdict(list)
        map(
            lambda u: users_by_alpha[u[0]].append(u),
            self.get_api_results(response)
        )

        self.render("userlist.html", page_title="Users", users_by_alpha=users_by_alpha)
