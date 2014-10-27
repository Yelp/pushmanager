import datetime
import json
import logging
import os
import urllib2

from pushmanager.core import util
from pushmanager.core.settings import Settings
from tornado.web import UIModule


class Request(UIModule):
    """Displays an individual request entry with expandable details/comments."""

    def javascript_files(self):
        return [self.handler.static_url('js/modules/request.js')]

    def css_files(self):
        return [self.handler.static_url('css/modules/request.css')]

    def render(self, request, **kwargs):
        kwargs.setdefault('edit_buttons', False) # Whether or not to show the 'Edit'/'Takeover' button
        kwargs.setdefault('expand', False) # Whether to automatically expand this entry (only used on /request)
        kwargs.setdefault('push_buttons', False) # Whether or not to show buttons related to push management
        kwargs.setdefault('pushmaster', False) # Whether or not to show pushmaster-related push buttons (Add/Remove)
        kwargs.setdefault('show_ago', False) # Whether or not to show relative time indicator at the beginning of the entry
        kwargs.setdefault('show_state_inline', False) # Whether or not to show state (requested, added, etc) at the end of the entry

        if request['repo'] != Settings['git']['main_repository']:
            kwargs['cherry_string'] = '%s/%s' % (request['repo'], request['branch'])
        else:
            kwargs['cherry_string'] = request['branch']

        if request['reviewid']:
            kwargs['review'] = {
                'url': "http://%s/r/%s" % (Settings['reviewboard']['servername'], request['reviewid']),
                'display': str(request['reviewid']),
            }
        else:
            kwargs['review'] = None

        repo = request['repo']
        if repo != Settings['git']['main_repository']:
            repo = os.path.join(Settings['git']['dev_repositories_dir'], repo)

        kwargs.setdefault('tags', self._generate_tag_list(request, repo))

        kwargs.setdefault('repo_url', 'https://%s/?p=%s.git;a=summary' % (
            Settings['git']['gitweb_servername'],
            repo
        ))
        kwargs.setdefault('branch_url', 'https://%s/?p=%s.git;a=log;h=refs/heads/%s' % (
            Settings['git']['gitweb_servername'],
            repo,
            request['branch']
        ))
        kwargs.setdefault('diff_url', 'https://%s/?p=%s.git;a=history;f=pushplans;hb=refs/heads/%s' % (
            Settings['git']['gitweb_servername'],
            repo,
            request['branch']
        ))
        kwargs.setdefault('web_hooks', Settings['web_hooks'])
        kwargs.setdefault('create_time', datetime.datetime.fromtimestamp(request['created']).strftime("%x %X"))
        kwargs.setdefault('modify_time', datetime.datetime.fromtimestamp(request['modified']).strftime("%x %X"))

        return self.render_string('modules/request.html', request=request, pretty_date=util.pretty_date, **kwargs)


    def _generate_tag_list(self, request, repo):
        tags = dict((tag, None) for tag in (request['tags'].split(',') if request['tags'] else []))

        if 'buildbot' in tags:
            tags['buildbot'] = "https://%s/rev/%s" % (Settings['buildbot']['servername'], request['revision'])


        if 'git-ok' in tags:
            tags['git-ok'] = 'https://%s/?p=%s.git;a=log;h=refs/heads/%s' % (
                Settings['git']['gitweb_servername'],
                repo,
                request['branch']
            )

        if 'pushplans' in tags:
            tags['pushplans'] = "https://%s/?p=%s.git;a=history;f=pushplans;hb=refs/heads/%s" % (
                Settings['git']['gitweb_servername'],
                repo,
                request['branch']
            )

        if 'tests_tag' in Settings and Settings['tests_tag']['tag'] in tags:
            tests_tag = Settings['tests_tag']['tag']
            try:
                api_url = Settings['tests_tag']['tag_api_endpoint'].replace('%SHA%', request['revision'])
                api_body = Settings['tests_tag']['tag_api_body'].replace('%SHA%', request['revision'])
                resp = urllib2.urlopen(api_url, api_body)
                tests_tag = json.loads(resp.read())['tag']
            except Exception as e:
                tests_tag += ': ERROR retrieving'
                logging.error(e)

            tags[tests_tag] = None
            if 'url_api_endpoint' in Settings['tests_tag']:
                try:
                    result_api_url = Settings['tests_tag']['url_api_endpoint'].replace('%SHA%', request['revision'])
                    result_api_body = Settings['tests_tag']['url_api_body'].replace('%SHA%', request['revision'])
                    resp = urllib2.urlopen(result_api_url, result_api_body)
                    results_url = json.loads(resp.read())['url']
                    if results_url != '':
                        tags[tests_tag] = results_url
                except Exception as e:
                    logging.warning(e)
                    logging.warning("Couldn't load results for results test URL from %s with body %s" %
                            (
                                Settings['tests_tag']['url_api_endpoint'].replace('%SHA%', request['revision']),
                                Settings['tests_tag']['url_api_body'].replace('%SHA%', request['revision'])
                            )
                        )


            del tags[Settings['tests_tag']['tag']]

        return sorted(tags.iteritems())

class NewRequestDialog(UIModule):
    """Displays a button which opens a dialog to create a new request."""

    def javascript_files(self):
        return [self.handler.static_url('js/modules/newrequest.js')]

    def css_files(self):
        return [self.handler.static_url('css/modules/newrequest.css')]

    def render(self):
        return self.render_string('modules/newrequest.html')
