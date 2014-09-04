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

        # divide people into groups, each group has 5 persons.
        groups = [people[i:i+5] for i in range(0, len(people), 5)]

        for i, group in enumerate(groups):
            irc_message = u'{0} {1}{2}'.format(
                '[[pushmaster %s]]' % self.current_user if not i else '',
                ', '.join(group),
                ': ' + message if i == len(groups) - 1 else '',
            )
            subprocess.call([
                '/nail/sys/bin/nodebot',
                '-i',
                irc_nick,
                Settings['irc']['channel'],
                irc_message
            ])
