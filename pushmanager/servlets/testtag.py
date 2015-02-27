import json
import logging
import urllib2

import tornado.web

from tornado.escape import url_escape
from tornado.escape import xhtml_escape

import pushmanager.core.util
from pushmanager.core.git import GitQueue
from pushmanager.core.requesthandler import RequestHandler
from pushmanager.core.settings import Settings


class TestTagServlet(RequestHandler):

    def _arg(self, key):
        return pushmanager.core.util.get_str_arg(self.request, key, '')

    @tornado.web.asynchronous
    def get(self):
        request_id = pushmanager.core.util.get_int_arg(self.request, 'id')
        resp = {}
        if not request_id:
            self.set_status(404)
        else:
            request = GitQueue._get_request(request_id)
            resp = self._gen_test_tag_resp(request)
        self.finish(resp)

    @classmethod
    def _gen_test_tag_resp(cls, request):
        response = {}

        if 'tests_tag' in Settings and Settings['tests_tag']['tag'] in request['tags']:
            response['tag'] = Settings['tests_tag']['tag']
            try:
                api_url = Settings['tests_tag']['tag_api_endpoint'].replace('%SHA%', request['revision'])
                api_body = Settings['tests_tag']['tag_api_body'].replace('%SHA%', request['revision'])
                api_resp = urllib2.urlopen(api_url, api_body)
                response['tag'] = xhtml_escape(json.loads(api_resp.read())['tag'])
            except Exception as e:
                response['tag'] += ": ERROR connecting to server"
                logging.error(e)

            response['url'] = ''
            if 'url_api_endpoint' in Settings['tests_tag']:
                try:
                    result_api_url = Settings['tests_tag']['url_api_endpoint'].replace('%SHA%', request['revision'])
                    result_api_url = result_api_url.replace('%BRANCH%', request['branch'])
                    result_api_body = Settings['tests_tag']['url_api_body'].replace('%SHA%', request['revision'])
                    result_api_body = result_api_body.replace('%BRANCH%', request['branch'])
                    resp = urllib2.urlopen(result_api_url, result_api_body)
                    result_id = url_escape(json.loads(resp.read())['id'])
                    if result_id != '':
                        response['url'] = Settings['tests_tag']['url_tmpl'].replace(
                            '%ID%',
                            result_id
                        ).replace(
                            '%SHA%',
                            request['revision']
                        )
                        response['url'] = response['url'].replace('%BRANCH%', request['branch'])
                except Exception as e:
                    logging.warning(e)
                    logging.warning(
                        "Couldn't load results for results test URL from %s with body %s" % (
                            Settings['tests_tag']['url_api_endpoint'].replace('%SHA%', request['revision']),
                            Settings['tests_tag']['url_api_body'].replace('%SHA%', request['revision'])
                        )
                    )
        return response
