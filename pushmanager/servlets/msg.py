import subprocess

from pushmanager.core.requesthandler import RequestHandler
from pushmanager.core.settings import Settings
from pushmanager.core.util import send_people_msg_in_groups
from pushmanager.core import db
import sqlalchemy as SA


class MsgServlet(RequestHandler):
    people = []

    def post(self):
        if not self.current_user:
            return self.send_error(403)

        push_id = self.request.arguments.get('id', [None])[0]
        if not push_id:
            return self.send_error(404)
        contents_query = self.generate_pushcontent_query(push_id)
        db.execute_cb(contents_query, self.get_push_request_users)
        people = self.people
        message = self.request.arguments.get('message', [None])[0]
        if not message:
            return self.send_error(500)

        irc_nick = Settings['irc']['nickname'].format(
            pushmaster=self.current_user
        )

        if not people:
            irc_message = u'[[pushmaster {0}]] {1}'.format(
                self.current_user,
                message,
            )

            subprocess.call([
                '/nail/sys/bin/nodebot',
                '-i',
                irc_nick,
                Settings['irc']['channel'],
                irc_message
            ])
            return

        send_people_msg_in_groups(
            people,
            message,
            irc_nick,
            Settings['irc']['channel'],
            person_per_group=5,
            prefix_msg='[[pushmaster %s]]' % self.current_user
        )

    def generate_pushcontent_query(self, push_id):
        state = self.request.arguments.get('state', [None])[0]
        contents_query = ''
        if state == 'requested':
            contents_query = db.push_requests.select(
                    db.push_pushcontents.c.push == push_id
            )
        else:
            contents_query = db.push_requests.select(
                SA.and_(
                    db.push_requests.c.id == db.push_pushcontents.c.request,
                    db.push_pushcontents.c.push == push_id,
                ),
                order_by=(db.push_requests.c.user, db.push_requests.c.title)
            )
        return contents_query

    def get_push_request_users(self, success, db_results):
        request_list = self.filter_request_by_state(success, db_results)
        people = []
        for request in request_list:
            people.append((request['user']))
            for watcher in request['watchers'].split(','):
                people.append((watcher))
        people = list(set(people))
        people = filter(None, people)
        self.people = people

    def filter_request_by_state(self, success, db_results):
        user_requests = []
        state = self.request.arguments.get('state', [None])[0]
        for request in db_results:
            if (state == 'all' and request['state'] != 'pickme') or (
                    state == request['state']):
                user_requests.append(request)
        return user_requests
