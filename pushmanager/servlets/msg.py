import subprocess

from pushmanager.core.requesthandler import RequestHandler
from pushmanager.core.settings import Settings
from pushmanager.core.util import send_people_msg_in_groups


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


        send_people_msg_in_groups(
                                    people, message, irc_nick,
                                    Settings['irc']['channel'],
                                    person_per_group=5,
                                    prefix_msg='[[pushmaster %s]]' % self.current_user
                                )
