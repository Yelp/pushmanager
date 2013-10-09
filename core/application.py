from abc import ABCMeta
from abc import abstractmethod
import daemon
import logging
import os
from optparse import OptionParser
import pwd
import sys
import time

import tornado.ioloop

from core import pid
from core.settings import Settings

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)-15s [%(process)d|%(threadName)s] %(message)s",
)


class Application:
    __metaclass__ = ABCMeta

    name = "NONE"

    def __init__(self):
        self.port = Settings['%s_app' % self.name]['port']
        self.pid_file = os.path.join(Settings['log_path'], '%s.%d.pid' % (self.name, self.port))
        self.log_file = os.path.join(Settings['log_path'], '%s.%d.log' % (self.name, self.port))
        self.log = open(self.log_file, 'a+')
        self.command = self.parse_command()

        self.clean_pids()

        if self.command == "stop":
            sys.exit()

    def parse_command(self):
        usage = "Usage: %prog start|stop"
        parser = OptionParser(usage=usage)
        _, args = parser.parse_args()

        if len(args) != 1 and args[0] not in ('start', 'stop'):
            parser.print_help()
            sys.exit(1)

        return args[0]

    def clean_pids(self):
        if os.path.exists(self.pid_file):
            pid.check(self.pid_file)
            os.unlink(self.pid_file)
            time.sleep(1)

    @abstractmethod
    def start_services(self):
        pass

    def run(self):
        daemon_context = daemon.DaemonContext(stdout=self.log, stderr=self.log, working_directory=os.getcwd())
        with daemon_context:
            pid.write(self.pid_file)
            try:
                self.start_services()
                pid.write(self.pid_file, append=True)

                # Drop privileges
                uid = pwd.getpwnam(Settings.get("username", "www-data"))[2]
                os.setuid(uid)

                tornado.ioloop.IOLoop.instance().start()
            finally:
                pid.remove(self.pid_file)
