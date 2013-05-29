# -*- coding: utf-8 -*-
from . import db
from .mail import MailQueue
import logging
from Queue import Queue
import subprocess
from threading import Thread
import time
from core.util import add_to_tags_str
from core.util import del_from_tags_str
from core.util import EscapedDict
from core.util import tags_contain
from urllib import urlencode
import urllib2

from core.settings import Settings

class GitCommand(subprocess.Popen):

    def __init__(self, *args, **kwargs):
        _args = ['git'] + list(args)
        _kwargs = {
            'stdout': subprocess.PIPE,
            'stderr': subprocess.PIPE,
        }
        _kwargs.update(kwargs)
        subprocess.Popen.__init__(self, _args, **_kwargs)

    def run(self):
        stdout, stderr = self.communicate()
        return self.returncode, stdout, stderr

class GitQueue(object):

    request_queue = Queue()
    worker_thread = None

    EXCLUDE_FROM_GIT_VERIFICATION = Settings['git']['exclude_from_verification']

    @classmethod
    def request_is_excluded_from_git_verification(cls, request):
        """Some tags modify the workflow and are excluded from repository
        verification.
        """
        return tags_contain(request['tags'], cls.EXCLUDE_FROM_GIT_VERIFICATION)

    @classmethod
    def start_worker(cls):
        if cls.worker_thread is not None:
            return
        cls.worker_thread = Thread(target=cls.process_queue, name='git-queue')
        cls.worker_thread.daemon = True
        cls.worker_thread.start()

    @classmethod
    def _get_repository_uri(cls, repository):
        scheme = Settings['git']['scheme']
        netloc = Settings['git']['servername']
        if Settings['git']['auth']:
            netloc = '%s@%s' % (Settings['git']['auth'], netloc)
        if Settings['git']['port']:
            netloc = '%s:%s' % (netloc, Settings['git']['port'])
        if repository == Settings['git']['main_repository']:
            repository = '%s://%s/%s' % (Settings['git']['scheme'], netloc, Settings['git']['main_repository'])
        else:
            repository = '%s://%s/%s/%s' % (Settings['git']['scheme'], netloc, Settings['git']['dev_repositories_dir'], repository)
        return repository

    @classmethod
    def _get_branch_sha_from_repo(cls, req):
        user_to_notify = req['user']
        repository = self._get_repository_uri(req['repo'])
        ls_remote = GitCommand('ls-remote', '-h', repository, req['branch'])
        rc, stdout, stderr = ls_remote.run()
        stdout = stdout.strip()
        query_details = {
            'user': req['user'],
            'title': req['title'],
            'repo': req['repo'],
            'branch': req['branch'],
            'repository': repository,
            'stderr': stderr,
        }
        if rc:
            msg = (
                """
                <p>
                    There was an error verifying your push request in Git:
                </p>
                <p>
                    <strong>%(user)s - %(title)s</strong><br />
                    <em>%(repo)s/%(branch)s</em>
                </p>
                <p>
                    Attempting to query the specified repository (%(repository)s) failed with
                    the following error(s):
                </p>
                <pre>
%(stderr)s
                </pre>
                <p>
                    Regards,<br/>
                    PushManager
                </p>
                """)
            msg %= EscapedDict(query_details)
            subject = '[push error] %s - %s' % (req['user'], req['title'])
            #MailQueue.enqueue_user_email([request_info['user']], msg, subject)
            MailQueue.enqueue_user_email([user_to_notify], msg, subject)
            return None

        # successful ls-remote, build up the refs list
        tokens = (tok for tok in stdout.split())
        refs = zip(tokens,tokens)
        for sha, ref in refs:
            if ref == ('refs/heads/%s' % req['branch']):
                return sha
        else:
            msg = (
                """
                <p>
                    There was an error verifying your push request in Git:
                </p>
                <p>
                    <strong>%(user)s - %(title)s</strong><br />
                    <em>%(repo)s/%(branch)s</em>
                </p>
                <p>
                    The specified branch (%(branch)s) was not found in the repository (%(repository)s).
                </p>
                <p>
                    Regards,<br/>
                    PushManager
                </p>
                """)
            msg %= EscapedDict(query_details)
            subject = '[push error] %s - %s' % (req['user'], req['title'])
            #MailQueue.enqueue_user_email([request_info['user']], msg, subject)
            MailQueue.enqueue_user_email([user_to_notify], msg, subject)
            return None

    @classmethod
    def _get_request(cls, request_id):
        result = [None]
        def on_db_return(success, db_results):
            assert success, "Database error."
            result[0] = db_results.first()

        request_info_query = db.push_requests.select().where(
            db.push_requests.c.id == request_id
        )
        db.execute_cb(request_info_query, on_db_return)
        req = result[0]
        if req:
            req = dict(req.items())
        return req

    @classmethod
    def _get_request_with_sha(cls, sha):
        result = [None]
        def on_db_return(success, db_results):
            assert success, "Database error."
            result[0] = db_results.first()

        request_info_query = db.push_requests.select().where(
            db.push_requests.c.revision == sha
        )
        db.execute_cb(request_info_query, on_db_return)
        req = result[0]
        if req:
            req = dict(req.items())
        return req

    @classmethod
    def _update_request(cls, req, updated_values):
        result = [None]
        def on_db_return(success, db_results):
            result[0]  = db_results[1].first()
            assert success, "Database error."

        update_query = db.push_requests.update().where(
                db.push_requests.c.id == req['id']
            ).values(updated_values)
        select_query = db.push_requests.select().where(
                db.push_requests.c.id == req['id']
            )
        db.execute_transaction_cb([update_query, select_query], on_db_return)

        updated_request = result[0]
        if updated_request:
            updated_request = dict(updated_request.items())
        if not updated_request:
            logging.error("Git-queue worker failed to update the request (id %s)." %  req['id'])
            logging.error("Updated Request values were: %s" % repr(updated_values))

        return updated_request

    @classmethod
    def update_request(cls, request_id):
        req = cls._get_request(request_id)
        if not req:
            # Just log this and return. We won't be able to get more
            # data out of the request.
            error_msg = "Git queue worker received a job for non-existent request id %s" % request_id
            logging.error(error_msg)
            return

        if cls.request_is_excluded_from_git_verification(req):
            return

        if not req['branch']:
            error_msg = "Git queue worker received a job for request with no branch (id %s)" % request_id
            return cls.update_request_failure(req, error_msg)

        sha = cls._get_branch_sha_from_repo(req)
        if sha is None:
            error_msg = "Git queue worker could not get the revision from request branch (id %s)" % request_id
            return cls.update_request_failure(req, error_msg)

        duplicate_req = cls._get_request_with_sha(sha)
        if duplicate_req and duplicate_req.has_key('state') and not duplicate_req['state'] == "discarded":
            error_msg = "Git queue worker found another request with the same revision sha (ids %s and %s)" % (
                duplicate_req['id'],
                request_id
            )
            return cls.update_request_failure(req, error_msg)

        updated_tags = add_to_tags_str(req['tags'], 'git-ok')
        updated_tags = del_from_tags_str(updated_tags, 'git-error')
        updated_values = {'revision': sha, 'tags': updated_tags}

        updated_request = cls._update_request(req, updated_values)
        if updated_request:
            cls.update_request_successful(updated_request)

    @classmethod
    def update_request_successful(cls, updated_request):
        msg = (
        """
        <p>
            PushManager has verified the branch for your request.
        </p>
        <p>
            <strong>%(user)s - %(title)s</strong><br />
            <em>%(repo)s/%(branch)s</em><br />
            <a href="https://%(pushmanager_servername)s/request?id=%(id)s">https://%(pushmanager_servername)s/request?id=%(id)s</a>
        </p>
        <p>
            Review # (if specified): <a href="https://%(reviewboard_servername)s/r/%(reviewid)s">%(reviewid)s</a>
        </p>
        <p>
            Verified revision: <code>%(revision)s</code><br/>
            <em>(If this is <strong>not</strong> the revision you expected,
            make sure you've pushed your latest version to the correct repo!)</em>
        </p>
        <p>
            Regards,<br/>
            PushManager
        </p>
        """)
        updated_request.update({
            'pushmanager_servername': Settings['main_app']['servername'],
            'reviewboard_servername': Settings['reviewboard']['servername']
        })
        msg %= EscapedDict(updated_request)
        subject = '[push] %s - %s' % (updated_request['user'], updated_request['title'])
        user_to_notify = updated_request['user']
        MailQueue.enqueue_user_email([user_to_notify], msg, subject)

        webhook_req(
            'pushrequest',
            updated_request['id'],
            'ref',
            updated_request['branch'],
        )

        webhook_req(
            'pushrequest',
            updated_request['id'],
            'commit',
            updated_request['revision'],
        )

        if updated_request['reviewid']:
            webhook_req(
                'pushrequest',
                updated_request['id'],
                'review',
                updated_request['reviewid'],
            )

    @classmethod
    def update_request_failure(cls, request, failure_msg):
        logging.error(failure_msg)
        updated_tags = add_to_tags_str(request['tags'], 'git-error')
        updated_tags = del_from_tags_str(updated_tags, 'git-ok')
        updated_values = {'tags': updated_tags}

        cls._update_request(request, updated_values)

        msg = (
        """
        <p>
            <em>PushManager could <strong>not</strong> verify the branch for your request.</em>
        </p>
        <p>
            <strong>%(user)s - %(title)s</strong><br />
            <em>%(repo)s/%(branch)s</em><br />
            <a href="https://%(pushmanager_servername)s/request?id=%(id)s">https://%(pushmanager_servername)s/request?id=%(id)s</a>
        </p>
        <p>
            <strong>Error message</strong>:<br />
            %(failure_msg)s
        </p>
        <p>
            Review # (if specified): <a href="https://%(reviewboard_servername)s/r/%(reviewid)s">%(reviewid)s</a>
        </p>
        <p>
            Verified revision: <code>%(revision)s</code><br/>
            <em>(If this is <strong>not</strong> the revision you expected,
            make sure you've pushed your latest version to the correct repo!)</em>
        </p>
        <p>
            Regards,<br/>
            PushManager
        </p>
        """)
        request.update({
            'failure_msg': failure_msg,
            'pushmanager_servername': Settings['main_app']['servername'],
            'reviewboard_servername': Settings['reviewboard']['servername']
        })
        msg %= EscapedDict(request)
        subject = '[push] %s - %s' % (request['user'], request['title'])
        user_to_notify = request['user']
        MailQueue.enqueue_user_email([user_to_notify], msg, subject)

    @classmethod
    def process_queue(cls):
        while True:
            # Throttle
            time.sleep(1)

            request_id = cls.request_queue.get()
            try:
                cls.update_request(request_id)
            except Exception:
                logging.error('THREAD ERROR:', exc_info=True)
            finally:
                cls.request_queue.task_done()

    @classmethod
    def enqueue_request(cls, request_id):
        cls.request_queue.put(request_id)

def webhook_req(left_type, left_token, right_type, right_token):
    webhook_url = Settings['web_hooks']['post_url']
    body=urlencode({
        'reason': 'pushmanager',
        'left_type': left_type,
        'left_token': left_token,
        'right_type': right_type,
        'right_token': right_token,
    })
    try:
        f = urllib2.urlopen(webhook_url, body, timeout=3)
        f.close()
    except urllib2.URLError:
        logging.error("Web hook POST failed:", exc_info=True)


__all__ = ['GitQueue']
