import logging
import time
from multiprocessing import JoinableQueue
from multiprocessing import Lock
from multiprocessing import Process

import xmpp

from pushmanager.core.settings import Settings

class XMPPQueue(object):

    MAX_RETRY_COUNT = 3
    retry_messages = {}
    retry_messages_lock = Lock()

    message_queue = None
    worker_process = None

    @classmethod
    def start_worker(cls):
        if cls.worker_process is not None:
            return []
        cls.message_queue = JoinableQueue()
        cls.worker_process = Process(target=cls.process_queue, name='xmpp-queue')
        cls.worker_process.daemon = True
        cls.worker_process.start()
        return [cls.worker_process.pid]

    @classmethod
    def _retry_message(cls, msg):
        ret = True
        cls.retry_messages_lock.acquire(True)

        cls.retry_messages[msg] = cls.retry_messages.get(msg, 0) + 1
        if cls.retry_messages[msg] >= cls.MAX_RETRY_COUNT:
            del cls.retry_messages[msg]
            ret = False

        cls.retry_messages_lock.release()
        return ret

    @classmethod
    def _del_retry_message(cls, msg):
        cls.retry_messages_lock.acquire(True)
        if cls.retry_messages.has_key(msg):
            del cls.retry_messages[msg]
        cls.retry_messages_lock.release()

    @classmethod
    def _process_queue_item(cls, jabber_client):
        msg = cls.message_queue.get(True) # Blocks until a message is queued
        recipient, message = msg

        # Apply alias mapping, if any exists
        aliases = Settings['aliases']
        if aliases:
            recipient = aliases.get(recipient, recipient)

        xmpp_message = xmpp.protocol.Message(recipient, message)
        try:
            jabber_client.send(xmpp_message)
            cls._del_retry_message(msg)
        except IOError, e:
            if cls._retry_message(msg):
                logging.warning("Couldn't send the message, will retry... %s" % repr(msg))
                cls.message_queue.put(msg)
            else:
                logging.error("Couldn't send the message %s" % repr(msg))
                logging.error(repr(e))
        except Exception, e:
            logging.error("Couldn't send the message %s" % repr(msg))
            logging.error(repr(e))
        finally:
            cls.message_queue.task_done()

    @classmethod
    def _xmpp_connect_and_auth(cls):
        # Open connection to XMPP server
        jabber_id = xmpp.protocol.JID(Settings['xmpp']['username'])

        logging.info("Connecting to XMPP server...")
        jabber_client = xmpp.Client(jabber_id.getDomain(), debug=[])
        connected = jabber_client.connect(server=(Settings['xmpp']['server'], 5222))
        if not connected:
            logging.error("Unable to connect to XMPP server!")
            return None

        logging.info("Connected to XMPP server - %s" % connected)

        authed = jabber_client.auth(jabber_id.getNode(), Settings['xmpp']['password'], resource=jabber_id.getResource())
        if not authed:
            logging.error("Unable to authenticate with XMPP server!")
            return None

        logging.info("Authenticated with XMPP server - %s" % authed)
        jabber_client.sendInitPresence()

        return jabber_client

    @classmethod
    def _xmpp_check_and_reconnect(cls, jabber_client):
        jabber_client.Process(1)
        if not jabber_client.isConnected():
            logging.warning("Client is disconnected from XMPP server, reconnecting...")
            jabber_client.reconnectAndReauth()

    @classmethod
    def process_queue(cls):
        while True:
            try:
                jabber_client = cls._xmpp_connect_and_auth()
                if not jabber_client:
                    return
                while True:
                    cls._process_queue_item(jabber_client)
                    cls._xmpp_check_and_reconnect(jabber_client)
            except Exception, e:
                logging.error("Error processing queue, retrying... %s" % e)
            finally:
                try:
                    jabber_client.disconnect()
                except IOError:
                    pass
            time.sleep(3)

    @classmethod
    def enqueue_xmpp(cls, recipients, message):
        if isinstance(recipients, (list,set,tuple)):
            # Flatten non-string iterables
            for recipient in recipients:
                cls.enqueue_xmpp(recipient, message)
        elif isinstance(recipients, (str,unicode)):
            if cls.message_queue is not None:
                cls.message_queue.put( (recipients, message) )
            else:
                logging.error("Could not enqueue XMPP message: XMPPQueue has not been initialized!")
        else:
            raise ValueError('Recipient(s) must be a string or iterable of strings')

    @classmethod
    def enqueue_user_xmpp(cls, recipients, *args, **kwargs):
        """Transforms a list of 'user' to 'user@default_domain', then invokes enqueue_xmpp."""
        domain = Settings['xmpp']['default_domain']
        if isinstance(recipients, (list,set,tuple)):
            recipients = ['%s@%s' % (recepient, domain) if '@' not in recepient else recepient for recepient in recipients]
        elif isinstance(recipients, (str,unicode)):
            recipients = '%s@%s' % (recipients, domain) if '@' not in recipients else recipients
        else:
            raise ValueError('Recipient(s) must be a string or iterable of strings')
        return cls.enqueue_xmpp(recipients, *args, **kwargs)

__all__ = ['XMPPQueue']
