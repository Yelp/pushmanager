import os

import tornado.gen
import tornado.web

from core.requesthandler import RequestHandler
from core.settings import Settings
import core.util

def _repo(base):
    dev_repos_dir = Settings['git']['dev_repositories_dir']
    main_repository = Settings['git']['main_repository']
    return os.path.join(dev_repos_dir, base) if base != main_repository else base

class PushServlet(RequestHandler):

    @tornado.web.asynchronous
    @tornado.web.authenticated
    @tornado.gen.engine
    def get(self):
        pushid = core.util.get_int_arg(self.request, 'id')
        override = core.util.get_int_arg(self.request, 'override')
        response = yield tornado.gen.Task(
                        self.async_api_call,
                        "pushdata",
                        {"id": pushid}
                    )

        push_info, push_requests, available_requests = self.get_api_results(response)

        if push_info['stageenv'] is None:
            push_info['stageenv'] = 'Stage'

        push_survey_url = Settings.get('push_survey_url', None)

        self.render(
            "push.html",
            page_title=push_info['title'],
            pushid=pushid,
            push_info=push_info,
            push_contents=push_requests,
            push_survey_url=push_survey_url,
            available_requests=available_requests,
            fullrepo=_repo,
            override=override
        )
