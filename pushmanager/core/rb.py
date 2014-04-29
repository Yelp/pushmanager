import base64
import httplib
import json
import logging
from Queue import Queue
from threading import Thread
import time
from urllib import urlencode

from pushmanager.core.settings import Settings

class RBQueue(object):

    review_queue = Queue()
    worker_thread = None

    @classmethod
    def start_worker(cls):
        if cls.worker_thread is not None:
            return
        cls.worker_thread = Thread(target=cls.process_queue, name='rb-queue')
        cls.worker_thread.daemon = True
        cls.worker_thread.start()

    @classmethod
    def process_queue(cls):
        while True:
            time.sleep(1)

            review_id = cls.review_queue.get()
            try:
                cls.mark_review_as_submitted(review_id)
            except Exception:
                logging.error("ReviewBoard queue worker encountered an error (review_id: %r)",
                    review_id, exc_info=True)
            finally:
                cls.review_queue.task_done()

    @classmethod
    def mark_review_as_submitted(cls, review_id):
        credentials = base64.b64encode("%s:%s" % (
            Settings['reviewboard']['username'],
            Settings['reviewboard']['password'],
        ))

        headers = {
            'Accept': 'application/json',
            'Authorization': 'Basic %s' % credentials,
            'Content-Type': 'application/x-www-form-urlencoded',
        }

        data = urlencode({'status': 'submitted'})

        conn = httplib.HTTPSConnection(Settings['reviewboard']['servername'])
        conn.request("PUT", "/api/review-requests/%d/" % review_id, data, headers)
        raw_result = conn.getresponse().read()
        try:
            result = json.loads(raw_result)
        except Exception:
            result = None
        conn.close()

        if not result or result.get('stat') != 'ok':
            logging.error("Unable to mark review %r as submitted (%r)",
                review_id, raw_result, exc_info=True)

    @classmethod
    def enqueue_review(cls, review_id):
        cls.review_queue.put(review_id)

__all__ = ['RBQueue']
