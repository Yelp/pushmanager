# -*- coding: utf-8 -*-
import email.mime.text
import logging
import smtplib
from Queue import Empty
from multiprocessing import JoinableQueue
from multiprocessing import Process

from pushmanager.core.settings import Settings

class MailQueue(object):

    message_queue = None
    worker_process = None
    smtp = None

    @classmethod
    def start_worker(cls):
        if cls.worker_process is not None:
            return
        cls.message_queue = JoinableQueue()
        cls.worker_process = Process(target=cls.process_queue, name='mail-queue')
        cls.worker_process.daemon = True
        cls.worker_process.start()

    @classmethod
    def process_queue(cls):
        # We double-nest 'while True' blocks here so that we can
        # try to re-use the same SMTP server connection for batches
        # of emails, but not keep it open for long periods without
        # any emails to send.
        while True:
            # Blocks indefinitely
            send_email_args = cls.message_queue.get(True)
            cls.smtp = smtplib.SMTP('127.0.0.1', 25)
            while True:
                cls._send_email(*send_email_args)
                try:
                    # Only blocks for 5 seconds max, raises Empty if still nothing
                    send_email_args = cls.message_queue.get(True, 5)
                except Empty:
                    # Done with this batch, use a blocking call to wait for the next
                    break
            cls.smtp.quit()

    @classmethod
    def _send_email(cls, recipient, message, subject, from_email):
        msg = email.mime.text.MIMEText(message, 'html')
        msg['Subject'] = subject
        msg['From'] = from_email
        msg['To'] = recipient
        cls.smtp.sendmail(from_email, [recipient], msg.as_string())
        other_recipients = set(Settings['mail']['notifyall']) - set([recipient])
        if other_recipients:
            msg = email.mime.text.MIMEText(message, 'html')
            msg['Subject'] = '[all] %s' % subject
            msg['From'] = Settings['mail']['from']
            msg['To'] = ', '.join(other_recipients)
            cls.smtp.sendmail(from_email, list(other_recipients), msg.as_string())
        cls.message_queue.task_done()

    @classmethod
    def enqueue_email(cls, recipients, message, subject='', from_email=Settings['mail']['from']):
        if isinstance(recipients, (list,set,tuple)):
            # Flatten non-string iterables
            for recipient in recipients:
                cls.enqueue_email(recipient, message, subject, from_email)
        elif isinstance(recipients, (str,unicode)):
            if cls.message_queue is not None:
                cls.message_queue.put( (recipients, message, subject, from_email) )
            else:
                logging.error("Failed to enqueue email: MailQueue not initialized")
        else:
            raise ValueError('Recipient(s) must be a string or iterable of strings')

    @classmethod
    def enqueue_user_email(cls, recipients, *args, **kwargs):
        """Transforms a list of 'user' to 'user@default_domain.com', then invokes enqueue_email."""
        domain = Settings['mail']['default_domain']
        recipients = ['%s@%s' % (recipient, domain) if '@' not in recipient else recipient for recipient in recipients]
        return cls.enqueue_email(recipients, *args, **kwargs)

__all__ = ['MailQueue']
