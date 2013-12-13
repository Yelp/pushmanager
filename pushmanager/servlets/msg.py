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

        irc_nick = Settings['irc']['nickname'].format(pushmaster=self.current_user)

        irc_message = '%s: %s' % (', '.join(people), message) if people else message
        subprocess.call([
                '/nail/sys/bin/nodebot',
                '-i',
                irc_nick,
                Settings['irc']['channel'],
                irc_message
        ])
