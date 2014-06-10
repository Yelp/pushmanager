# -*- coding: utf-8 -*-
from . import db
from .mail import MailQueue
import os
import logging
from Queue import Queue
import subprocess
from threading import Thread
import time
from pushmanager.core.util import add_to_tags_str
from pushmanager.core.util import del_from_tags_str
from pushmanager.core.util import EscapedDict
from pushmanager.core.util import tags_contain
from urllib import urlencode
import urllib2

from pushmanager.core.settings import Settings

class GitBranchContextManager(object):
    """
    Context manager that creates / deletes a temporary git branch

    :param test_branch: The name of the temporary branch to create
    :param master_repo_path: The on-disk path to the master repository
    """

    def __init__(self, test_branch, master_repo_path):
        self.test_branch = test_branch
        self.master_repo_path = master_repo_path

    def __enter__(self):
        # Create a new branch tracking master
        make_test_branch = GitCommand(
            "checkout",
            "origin/master",
            "-b",
            self.test_branch,
            cwd=self.master_repo_path
        )
        rc, stdout, stderr = make_test_branch.run()
        if rc:
            raise Exception(
                "GitBranchContextManager",
                "Failed to create test branch: %s" % stderr
            )

    def __exit__(self, type, value, traceback):
        # Checkout master so that we can delete the test branch
        checkout_master = GitCommand(
            "checkout",
            "master",
            cwd = self.master_repo_path
        )
        rc, stdout, stderr = checkout_master.run()
        if rc:
            raise Exception(
                "GitBranchContextManager",
                "Unable to checkout master: %s"
                % self.test_branch
            )

        # Delete the branch that we were working on
        delete_test_branch = GitCommand(
            "branch",
            "-D",
            self.test_branch,
            cwd = self.master_repo_path
        )
        rc, stdout, stderr = delete_test_branch.run()
        if rc:
            raise Exception(
                "GitBranchContextManager",
                "Unable to delete test branch: %s"
                % self.test_branch
            )

def git_reset_to_ref(starting_ref, git_directory):
    """
    Resets a git repo to the specified ref.
    Called as a cleanup fn by GitMergeContextManager.

    :param starting_ref: Git hash of the commit to roll back to
    """

    reset_command = GitCommand(
        "reset",
        "--hard",
        starting_ref,
        cwd = git_directory
    )
    return reset_command.run()

class GitMergeContextManager(object):
    """
    Contest manager for merging that rolls back on __exit__

    :param test_branch: The name of the branch to merge onto
    :param master_repo_path: The on-disk path to the master repository
    :param pickme_request: A dictionary containing the details of the pickme
    """

    def __init__(self, test_branch, master_repo_path, pickme_request):
        self.test_branch = test_branch
        self.master_repo_path = master_repo_path
        self.pickme_request = pickme_request

    def __enter__(self):
        # Store the starting ref so that we can hard reset if need be
        get_starting_ref = GitCommand(
            "rev-parse",
            self.test_branch,
            cwd=self.master_repo_path
        )
        rc, stdout, stderr = get_starting_ref.run()
        if rc:
            raise Exception(
                "GitContextManager",
                "Failed to get current ref: %s" % stderr
            )
        self.starting_ref = stdout.strip()

        # Locate and merge the branch we are testing
        summary = "{branch_title}\n\n(Merged from {user}/{branch})".format(
            branch_title = self.pickme_request['title'],
            user = self.pickme_request['user'],
            branch = self.pickme_request['branch']
        )
        pickme_repo_uri = "/var/lib/pushmanager/repos/%s" % self.pickme_request['user']
        pull_command = GitCommand(
            "pull",
            "--no-ff",
            "--no-commit",
            pickme_repo_uri,
            self.pickme_request['branch'],
            cwd = self.master_repo_path)
        rc, stdout, stderr = pull_command.run()
        if rc:
            git_reset_to_ref(self.starting_ref, self.master_repo_path)
            raise Exception(
                "GitContextManager",
                "Unable to merge branch %s" % self.pickme_request['branch']
            )

        ##TODO: Submodules

        commit_command = GitCommand("commit", "-m", summary, "--no-verify", cwd=self.master_repo_path)
        rc, stdout, stderr = commit_command.run()
        if rc:
            git_reset_to_ref(self.starting_ref, self.master_repo_path)
            raise Exception(
                "GitContextManager",
                "Committing branch %s failed! One possible cause: a branch which contains no changes (nothing to commit)"
                % self.pickme_request['branch']
            )

    def __exit__(self, type, value, traceback):
        rc, stdout, stderr = git_reset_to_ref(
            self.starting_ref,
            self.master_repo_path
        )
        if rc:
            raise Exception(
                "GitContextManager",
                "Failed to reset branch %s: %s"
                % (self.pickme_request['branch'], stderr)
            )



class GitTaskAction:
    VERIFY_BRANCH, TEST_PICKME_CONFLICT = range(2)

class GitQueueTask(object):
    """
    A task for the GitQueue to perform.
    Task can be one of:
    - VERIFY_BRANCH: check that a branch can be found and is not a duplicate
    - TEST_PICKME_CONFLICT: check which (if any) branches also pickme'd for the
        same push cause merge conflicts with this branch
    """

    def __init__(self, task_type, request_id):
        self.task_type = task_type
        self.request_id = request_id

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
    def create_or_update_local_repo(cls, repo_name, branch):
        """
        Clones or fetches the repository specified by repo_name into the local_repo_path
        speficied in the configuration.
        If branch is specified, it will also checkout that branch.
        """

        repo_path = cls._get_local_repository_uri(repo_name)

        if not os.path.isdir(repo_path):
            # Clone the main repo into repo_path. Will take time!
            clone_repo = GitCommand(
                'clone',
                cls._get_repository_uri(repo_name),
                repo_path
            )
            rc, stdout, stderr = clone_repo.run()
            if rc:
                logging.error("Failed to create local clone with code %d: %s" % (rc, stderr))
                return rc

        # Fetch all new repo info
        fetch_updates = GitCommand('fetch', '--all', cwd=repo_path)
        rc, stdout, stderr = fetch_updates.run()
        if rc:
            logging.error("Failed to update local git repo (code %d): %s" % (rc, stderr))
            return rc

        # Checkout the branch
        checkout_branch = GitCommand('checkout', branch, cwd=repo_path)
        rc, stdout, stderr = checkout_branch.run()
        if rc:
            logging.error(
                "Failed to check out branch %s from %s (code %d): %s"
                % (branch, repo_name, rc, stderr)
            )
            return rc

        # Try to fast-forward any updates to the branch
        fetch_updates = GitCommand('pull', '--ff-only', cwd=repo_path)
        rc, stdout, stderr = fetch_updates.run()
        if rc:
            logging.error("Failed to update local git repo (code %d): %s" % (rc, stderr))
            return rc

        return 0

    @classmethod
    def _get_local_repository_uri(cls, repository):
        return os.path.join(Settings['git']['local_repo_path'], repository)

    @classmethod
    def _get_repository_uri(cls, repository):
        scheme = Settings['git']['scheme']
        netloc = Settings['git']['servername']
        if Settings['git']['auth']:
            netloc = '%s@%s' % (Settings['git']['auth'], netloc)
        if Settings['git']['port']:
            netloc = '%s:%s' % (netloc, Settings['git']['port'])
        if repository == Settings['git']['main_repository']:
            repository = '%s://%s/%s' % (scheme, netloc, Settings['git']['main_repository'])
        else:
            repository = '%s://%s/%s/%s' % (scheme, netloc, Settings['git']['dev_repositories_dir'], repository)
        return repository

    @classmethod
    def _get_branch_sha_from_repo(cls, req):
        # Update local copy of the repo
        cls.create_or_update_local_repo(req['repo'], branch=req['branch'])

        user_to_notify = req['user']
        repository = cls._get_local_repository_uri(req['repo'])
        ls_remote = GitCommand('ls-remote', '-h', repository, req['branch'])
        rc, stdout, stderr = ls_remote.run()
        stdout = stdout.strip()
        query_details = {
            'user': req['user'],
            'title': req['title'],
            'repo': req['repo'],
            'branch': req['branch'],
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
                    Attempting to query the specified repository failed with
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
                    The specified branch (%(branch)s) was not found in the repository.
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
    def _get_request_ids_in_push(cls, push_id):
        pickme_list = []

        def on_db_return(success, db_results):
            assert success, "Database error."
            for (request, push) in db_results:
                pickme_list.append(str(request))

        request_info_query = db.push_pushcontents.select().where(
            db.push_pushcontents.c.push == int(push_id)
        )
        db.execute_cb(request_info_query, on_db_return)
        return pickme_list

    @classmethod
    def _get_push_for_request(cls, request_id):
        result = [None]
        def on_db_return(success, db_results):
            assert success, "Database error."
            result[0] = db_results.first()

        request_info_query = db.push_pushcontents.select().where(
            db.push_pushcontents.c.request == request_id
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
    def test_pickme_conflicts(cls, request_id):
        # Get the push this branch is associated with (requests can only be associated with one push)
        # Get other pickmes in that push
        # Apply this branch
        # Apply each of the others in turn, check for errors

        req = cls._get_request(request_id)
        if not req:
            logging.error("Tried to test conflicts for non-existent request id %s" % request_id)
            return

        push = cls._get_push_for_request(request_id)
        if not push:
            logging.error("Request %d (%s) doesn't seem to be part of a push" % (request_id, req['title']))
            return
        push_id = push['push']

        #### Set up the environment as though we are preparing a deploy push
        ## Create a branch pickme_test_PUSHID_PICKMEID

        # Update local copy of the pickme'd repo and the master repo
        cls.create_or_update_local_repo(req['repo'], branch=req['branch'])
        cls.create_or_update_local_repo(Settings['git']['main_repository'], branch="master")

        # Get base paths and names for the relevant repos
        repo_path = cls._get_local_repository_uri(Settings['git']['main_repository'])
        target_branch = "pickme_test_{push_id}_{pickme_id}".format(
            push_id = push_id,
            pickme_id = request_id
        )

        # Remove the conflict-master and conflict-pickme tags
        updated_tags = del_from_tags_str(req['tags'], 'conflict-master')
        updated_tags = del_from_tags_str(updated_tags, 'conflict-pickme')

        # Create a test branch following master
        with GitBranchContextManager(target_branch, repo_path):
            # Merge the pickme we are testing onto the test branch
            # If this fails, that means pickme conflicts with master
            try:
                with GitMergeContextManager(target_branch, repo_path, req):
                    # If we get here, it doesn't conflict with master
                    # Get a list of (other) pickmes in the push
                    pickme_ids = cls._get_request_ids_in_push(push_id)
                    pickme_ids = [ p for    p in pickme_ids if p != request_id]

                    conflict_pickmes = []

                    logging.error("Comparing pickme %s with pickme(s): %s"
                        % (request_id, pickme_ids))

                    # For each pickme, check if merging it on top throws an exception.
                    # If it does, keep track of the pickme in conflict_pickmes
                    for pickme in pickme_ids:
                        pickme_details = cls._get_request(pickme)
                        if not pickme_details:
                            logging.error("Tried to test for conflicts against non-existent request id %s" % request_id)
                            continue

                        # Don't bother trying to compare against pickmes that
                        # break master, as they will conflict by default
                        if not "conflict-master" in pickme_details['tags']:
                            try:
                                with GitMergeContextManager(target_branch, repo_path, pickme_details):
                                    pass
                            except Exception, e:
                                conflict_pickmes.append((pickme, e))

                    logging.info("Pickme %s conflicted with %d pickmes: %s"
                        % (request_id, len(conflict_pickmes), conflict_pickmes))
                    if len(conflict_pickmes) > 0:
                        updated_tags = add_to_tags_str(updated_tags, 'conflict-pickme')
                    formatted_conflicts = "";
                    for broken_pickme, error in conflict_pickmes:
                        pickme_details = cls._get_request(broken_pickme)
                        formatted_pickme_err = "Conflict with <a href='/request?id={pickme_id}'>{pickme_name}</a>: <br/>{pickme_err}<br/><br/>".format(
                            pickme_id = broken_pickme,
                            pickme_err = error,
                            pickme_name = pickme_details['title']
                        )
                        formatted_conflicts += formatted_pickme_err

                    updated_values = {
                        'tags': updated_tags,
                        'conflicts': formatted_conflicts
                    }

                    updated_request = cls._update_request(req, updated_values)
                    if not updated_request:
                        logging.error("Failed to update pickme")


            except Exception, e:
                logging.info("Pickme %s conflicted with master: %s"
                        % (request_id, repr(e)))
                updated_tags = add_to_tags_str(updated_tags, 'conflict-master')
                updated_values = {
                        'tags': updated_tags,
                        'conflicts': "<strong>Conflict with master:</strong><br/> %s" % repr(e)
                    }

                updated_request = cls._update_request(req, updated_values)
                if not updated_request:
                    logging.error("Failed to update pickme")

    @classmethod
    def verify_branch(cls, request_id):
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
            return cls.verify_branch_failure(req, error_msg)

        sha = cls._get_branch_sha_from_repo(req)
        if sha is None:
            error_msg = "Git queue worker could not get the revision from request branch (id %s)" % request_id
            return cls.verify_branch_failure(req, error_msg)

        duplicate_req = cls._get_request_with_sha(sha)
        if duplicate_req and duplicate_req.has_key('state') and not duplicate_req['state'] == "discarded":
            error_msg = "Git queue worker found another request with the same revision sha (ids %s and %s)" % (
                duplicate_req['id'],
                request_id
            )
            return cls.verify_branch_failure(req, error_msg)

        updated_tags = add_to_tags_str(req['tags'], 'git-ok')
        updated_tags = del_from_tags_str(updated_tags, 'git-error')
        updated_values = {'revision': sha, 'tags': updated_tags}

        updated_request = cls._update_request(req, updated_values)
        if updated_request:
            cls.verify_branch_successful(updated_request)

    @classmethod
    def verify_branch_successful(cls, updated_request):
        msg = (
        """
        <p>
            PushManager has verified the branch for your request.
        </p>
        <p>
            <strong>%(user)s - %(title)s</strong><br />
            <em>%(repo)s/%(branch)s</em><br />
            <a href="https://%(pushmanager_servername)s%(pushmanager_port)s/request?id=%(id)s">https://%(pushmanager_servername)s%(pushmanager_port)s/request?id=%(id)s</a>
        </p>
        <p>
            Review # (if specified): <a href="https://%(reviewboard_servername)s%(pushmanager_port)s/r/%(reviewid)s">%(reviewid)s</a>
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
            'pushmanager_port': ':%d' % Settings['main_app']['port'] if Settings['main_app']['port'] != 443 else '',
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
    def verify_branch_failure(cls, request, failure_msg):
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

            task = cls.request_queue.get()

            if not isinstance(task, GitQueueTask):
                logging.error("Non-task object in GitQueue: %s" % task)
                continue

            try:
                if task.task_type is GitTaskAction.VERIFY_BRANCH:
                    cls.verify_branch(task.request_id)
                elif task.task_type is GitTaskAction.TEST_PICKME_CONFLICT:
                    cls.test_pickme_conflicts(task.request_id)
                else:
                    logging.error("GitQueue encountered unknown task type %d" % task.task_type)
            except Exception:
                logging.error('THREAD ERROR:', exc_info=True)
            finally:
                cls.request_queue.task_done()

    @classmethod
    def enqueue_request(cls, task_type, request_id):
        cls.request_queue.put(GitQueueTask(task_type, request_id))

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
