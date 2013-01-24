import subprocess
import time

import core.db as db
from core.settings import Settings
from core.requesthandler import RequestHandler
import core.util
from core.xmppclient import XMPPQueue

class NewPushServlet(RequestHandler):

    def _arg(self, key):
        return core.util.get_str_arg(self.request, key, '')

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
        if self.pushtype in ('private', 'morning'):
            people = None
        elif self.pushtype == 'urgent':
            people = set(x['user'] for x in select_results if 'urgent' in x['tags'].split(','))
        else:
            people = set(x['user'] for x in select_results)

        pushmanager_servername = Settings['main_app']['servername']
        pushmanager_url = "https://%s%s" % (pushmanager_servername, pushurl)
        if people:
            subprocess.call([
                '/nail/sys/bin/nodebot',
                '-i',
                Settings['irc']['nickname'],
                Settings['irc']['channel'],
                '%s: %s push starting! %s' % (', '.join(people), self.pushtype, pushmanager_url),
            ])
            XMPPQueue.enqueue_user_xmpp(people, 'Push starting! %s' % pushmanager_url)
        elif self.pushtype == 'morning':
            subprocess.call([
                '/nail/sys/bin/nodebot',
                '-i',
                Settings['irc']['nickname'],
                Settings['irc']['channel'],
                'Morning push opened. %s' % (pushmanager_servername,),
            ])
        return self.redirect(pushurl)
