import subprocess

from core.requesthandler import RequestHandler
from core.settings import Settings

class MsgServlet(RequestHandler):

    def post(self):
        if not self.current_user:
            return self.send_error(403)

        people = self.request.arguments.get('people[]', [])
        message = self.request.arguments.get('message', [None])[0]
        if not message:
            return self.send_error(500)

        irc_message = '%s: %s' % (', '.join(people), message) if people else message
        subprocess.call([
                '/nail/sys/bin/nodebot',
                '-i',
                Settings['irc']['nickname'],
                Settings['irc']['channel'],
                irc_message
        ])
