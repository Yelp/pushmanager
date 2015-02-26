import subprocess
import time

import pushmanager.core.db as db
import pushmanager.core.util
from pushmanager.core.mail import MailQueue
from pushmanager.core.requesthandler import RequestHandler
from pushmanager.core.settings import Settings
from pushmanager.core.xmppclient import XMPPQueue
from pushmanager.core.util import send_people_msg_in_groups


def send_notifications(people, pushtype, pushmanager_url):
    pushmanager_servername = Settings['main_app']['servername']

    if people:
        msg = '%s: %s push starting! %s' % (', '.join(people), pushtype, pushmanager_url)
        XMPPQueue.enqueue_user_xmpp(people, 'Push starting! %s' % pushmanager_url)
    elif pushtype == 'morning':
        msg = 'Morning push opened. %s' % pushmanager_servername
    else:
        msg = 'push starting. %s' % pushmanager_url

    if people:
        send_people_msg_in_groups(
            people, "%s push starting! %s" % (pushtype, pushmanager_url),
            Settings['irc']['nickname'], Settings['irc']['channel'],
            person_per_group=5, prefix_msg=''
        )
    else:
        subprocess.call([
            '/nail/sys/bin/nodebot',
            '-i',
            Settings['irc']['nickname'],
            Settings['irc']['channel'],
            msg
        ])

    subject = "New push notification"
    MailQueue.enqueue_user_email(Settings['mail']['notifyall'], msg, subject)


class NewPushServlet(RequestHandler):

    def _arg(self, key):
        return pushmanager.core.util.get_str_arg(self.request, key, '')

    def post(self):
        if not self.current_user:
            return self.send_error(403)
        self.pushtype = self._arg('push-type')
        insert_query = db.push_pushes.insert({
            'title': self._arg('push-title'),
            'user': self.current_user,
            'branch': self._arg('push-branch'),
            'revision': "0"*40,
            'created': time.time(),
            'modified': time.time(),
            'state': 'accepting',
            'pushtype': self.pushtype,
            })
        select_query = db.push_requests.select().where(
            db.push_requests.c.state == 'requested',
        )
        db.execute_transaction_cb([insert_query, select_query], self.on_db_complete)

    get = post

    def on_db_complete(self, success, db_results):
        self.check_db_results(success, db_results)

        insert_results, select_results = db_results
        pushurl = '/push?id=%s' % insert_results.lastrowid
        pushmanager_url = self.get_base_url() + pushurl

        def users_involved(request):
            if request['watchers']:
                return [request['user']] + request['watchers'].split(',')
            return [request['user']]

        if self.pushtype in ('private', 'morning'):
            people = None
        elif self.pushtype == 'urgent':
            people = set(user for x in select_results for user in users_involved(x) if 'urgent' in x['tags'].split(','))
        else:
            people = set(user for x in select_results for user in users_involved(x))

        send_notifications(people, self.pushtype, pushmanager_url)

        return self.redirect(pushurl)
