import subprocess
import time

import pushmanager.core.db as db
from pushmanager.core.mail import MailQueue
from pushmanager.core.settings import Settings
from pushmanager.core.requesthandler import RequestHandler
import pushmanager.core.util
from pushmanager.core.xmppclient import XMPPQueue

def send_notifications(people, pushtype, pushurl):
    pushmanager_servername = Settings['main_app']['servername']
    pushmanager_servername = pushmanager_servername.rstrip('/')
    pushmanager_port = ':%d' % Settings['main_app']['port'] if Settings['main_app']['port'] != 443 else ''

    pushurl = pushurl.lstrip('/')
    pushmanager_url = "https://%s/%s" % (pushmanager_servername + pushmanager_port, pushurl)

    if people:
        msg = '%s: %s push starting! %s' % (', '.join(people), pushtype, pushmanager_url)
        XMPPQueue.enqueue_user_xmpp(people, 'Push starting! %s' % pushmanager_url)
    elif pushtype == 'morning':
        msg = 'Morning push opened. %s' % pushmanager_servername
    else:
        msg = 'push starting. %s' % pushmanager_url

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

        send_notifications(people, self.pushtype, pushurl)

        return self.redirect(pushurl)
