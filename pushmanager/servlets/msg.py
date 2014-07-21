import subprocess

from pushmanager.core.requesthandler import RequestHandler
from pushmanager.core.settings import Settings


class MsgServlet(RequestHandler):

    def post(self):
        if not self.current_user:
            return self.send_error(403)

        people = self.request.arguments.get('people[]', [])
        message = self.request.arguments.get('message', [None])[0]
        if not message:
            return self.send_error(500)

        irc_nick = Settings['irc']['nickname'].format(
            pushmaster=self.current_user
        )

        irc_message = u'[[pushmaster {0}]] {1}{2}'.format(
            self.current_user,
            ', '.join(people) + ': ' if people else '',
            message,
        )
        subprocess.call([
                '/nail/sys/bin/nodebot',
                '-i',
                irc_nick,
                Settings['irc']['channel'],
                irc_message
        ])
