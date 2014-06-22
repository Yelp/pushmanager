# -*- coding: utf-8 -*-
from . import db
from .mail import MailQueue
import os
import logging
import subprocess
from multiprocessing import Process, JoinableQueue
import time
from pushmanager.core.util import add_to_tags_str
from pushmanager.core.util import del_from_tags_str
from pushmanager.core.util import EscapedDict
from pushmanager.core.util import tags_contain
from pushmanager.core.xmppclient import XMPPQueue
from urllib import urlencode
import urllib2

from pushmanager.core.settings import Settings

class GitException(Exception):
    """
    Exception class to be thrown by Git Context managers.
    Has fields for git output on top of  basic exception information.

    :param gitrc: Return code from the failing Git process
    :param gitout: Stdout for the git process
    :param giterr: Stderr for the git process
    """
    def __init__(self, details, gitrc=None, gitout=None, giterr=None, gitcwd=None):
        self.details = details
        self.gitrc = gitrc
        self.gitout = gitout
        self.giterr = giterr
        self.gitcwd = gitcwd

    def __str__(self):
        return repr((self.details, self.gitout, self.giterr, self.gitcwd))

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
        make_test_branch.run()

    def __exit__(self, type, value, traceback):
        # Checkout master so that we can delete the test branch
        checkout_master = GitCommand(
            "checkout",
            "master",
            cwd = self.master_repo_path
        )
        checkout_master.run()

        # Delete the branch that we were working on
        delete_test_branch = GitCommand(
            "branch",
            "-D",
            self.test_branch,
            cwd = self.master_repo_path
        )
        delete_test_branch.run()

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

        self.starting_ref = stdout.strip()

        # Locate and merge the branch we are testing
        summary = "{branch_title}\n\n(Merged from {user}/{branch})".format(
            branch_title = self.pickme_request['title'],
            user = self.pickme_request['user'],
            branch = self.pickme_request['branch']
        )

        try:
            pull_command = GitCommand(
                "pull",
                "--no-ff",
                "--no-commit",
                self.pickme_request['user'],
                self.pickme_request['branch'],
                cwd = self.master_repo_path)
            pull_command.run()

            commit_command = GitCommand("commit", "-m", summary, "--no-verify", cwd=self.master_repo_path)
            commit_command.run()
        except GitException, e:
            git_reset_to_ref(
                self.starting_ref,
                self.master_repo_path
            )
            raise e

    def __exit__(self, type, value, traceback):
        git_reset_to_ref(
            self.starting_ref,
            self.master_repo_path
        )



class GitTaskAction:
    VERIFY_BRANCH, TEST_PICKME_CONFLICT, TEST_ALL_PICKMES = range(3)

class GitQueueTask(object):
    """
    A task for the GitQueue to perform.
    Task can be one of:
    - VERIFY_BRANCH: check that a branch can be found and is not a duplicate
    - TEST_PICKME_CONFLICT: check which (if any) branches also pickme'd for the
        same push cause merge conflicts with this branch
    - TEST_ALL_PICKMES: Takes a push id, and queues every pushme with
        TEST_PICKME_CONFLICT. Used when an item is de-pickmed to ensure that
        anything it might have conlficted with is unmarked
    """

    def __init__(self, task_type, request_id, **kwargs):
        self.task_type = task_type
        self.request_id = request_id
        self.kwargs = kwargs

class GitCommand(subprocess.Popen):

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        _args = ['git'] + list(args)
        _kwargs = {
            'stdout': subprocess.PIPE,
            'stderr': subprocess.PIPE,
        }
        _kwargs.update(kwargs)
        subprocess.Popen.__init__(self, _args, **_kwargs)

    def run(self):
        stdout, stderr = self.communicate()
        if self.returncode:
            raise GitException(
                "GitException: git %s " % ' '.join(self.args),
                gitrc = self.returncode,
                giterr = stderr,
                gitout = stdout,
                gitcwd = self.kwargs['cwd'] if 'cwd' in self.kwargs else None
            )
        return self.returncode, stdout, stderr

class GitQueue(object):

    request_queue = None
    worker_process = None

    EXCLUDE_FROM_GIT_VERIFICATION = Settings['git']['exclude_from_verification']

    @classmethod
    def request_is_excluded_from_git_verification(cls, request):
        """Some tags modify the workflow and are excluded from repository
        verification.
        """
        return tags_contain(request['tags'], cls.EXCLUDE_FROM_GIT_VERIFICATION)

    @classmethod
    def start_worker(cls):
        if cls.worker_process is not None:
            return
        cls.request_queue = JoinableQueue()
        cls.worker_process = Process(target=cls.process_queue, name='git-queue')
        cls.worker_process.daemon = True
        cls.worker_process.start()

    @classmethod
    def create_or_update_local_repo(cls, repo_name, branch):
        """
        Clones the main repository if it does not exist.
        If repo_name is not the main repo, add that repo as a remote and fetch
        refs before checking out the specified branch.
        """

        # Since we are keeping everything in the same repo, repo_path should always be
        # the same
        repo_path = cls._get_local_repository_uri(Settings['git']['main_repository'])

        # repo_name is the remote to use. If we are dealing with the main repository,
        # set the remote to origin.
        if repo_name is Settings['git']['main_repository']:
            repo_name = 'origin'

        # Check if the main repo does not exist and needs to be created
        if not os.path.isdir(repo_path):
            # If we are using a reference mirror, add --reference [path] to
            # the list of gitcommand args
            clone_args = ['clone', cls._get_repository_uri(repo_name)]

            logging.error("Use local git mirror? %s" % repr(Settings['git']['use_local_mirror']))

            if Settings['git']['use_local_mirror']:
                if os.path.isdir(Settings['git']['local_mirror']):
                    clone_args.extend([
                        '--reference',
                        Settings['git']['local_mirror']
                    ])

            clone_args.append(repo_path)
            # Clone the main repo into repo_path. Will take time!
            clone_repo = GitCommand(*clone_args)
            clone_repo.run()

        # If we are dealing with a dev repo, make sure it is added as a remote
        dev_repo_uri = cls._get_repository_uri(repo_name)
        add_remote = GitCommand('remote', 'add', repo_name, dev_repo_uri, cwd=repo_path)
        try:
            add_remote.run()
        except GitException, e:
            # If the remote already exists, git will return err 128
            if e.gitrc is 128:
                pass
            else:
                raise e

        # Fetch all new repo info
        fetch_updates = GitCommand('fetch', '--all', cwd=repo_path)
        fetch_updates.run()

        # Checkout the branch
        full_branch = "%s/%s" % (repo_name, branch)
        checkout_branch = GitCommand('checkout', full_branch, cwd=repo_path)
        checkout_branch.run()

        # Update submodules
        sync_submodule = GitCommand("submodule", "--quiet", "sync", cwd=repo_path)
        sync_submodule.run()
        update_submodules = GitCommand("submodule", "--quiet", "update", "--init", cwd=repo_path)
        update_submodules.run()

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
        query_details = {
            'user': req['user'],
            'title': req['title'],
            'repo': req['repo'],
            'branch': req['branch'],
        }
        try:
            cls.create_or_update_local_repo(req['repo'], branch=req['branch'])

            user_to_notify = req['user']
            ls_remote = GitCommand('ls-remote', '-h', req['user'], req['branch'])
            rc, stdout, stderr = ls_remote.run()
            stdout = stdout.strip()
        except GitException, e:
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
            query_details['stderr'] = e.giterr
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
    def _test_pickme_conflict_pickme(cls, req, target_branch, repo_path, no_requeue):
        """
        Test for any pickmes that are broken by pickme'd request req

        Precondition: We should already be on a test branch, and the pickme to
        be tested against should already be successfully merged.

        :param req: Details for pickme to test against
        """

        push = cls._get_push_for_request(req['id'])
        pickme_ids = cls._get_request_ids_in_push(push['push'])
        logging.error("Candidate pickmes to compare against: %s", pickme_ids)

        pickme_ids = [ p for p in pickme_ids if int(p) != int(req['id'])]

        conflict_pickmes = []
        logging.error("Comparing pickme %s with pickme(s): %s"
            % (req['id'], pickme_ids))

        # For each pickme, check if merging it on top throws an exception.
        # If it does, keep track of the pickme in conflict_pickmes
        for pickme in pickme_ids:
            pickme_details = cls._get_request(pickme)
            if not pickme_details:
                logging.error("Tried to test for conflicts against non-existent request id %s" % pickme)
                continue

            # Don't bother trying to compare against pickmes that
            # break master, as they will conflict by default
            if "conflict-master" in pickme_details['tags']:
                continue

            try:
                with GitMergeContextManager(target_branch, repo_path, pickme_details):
                    pass
            except GitException, e:
                conflict_pickmes.append((pickme, e.gitout, e.giterr))
                # Requeue the conflicting pickme so that it also picks up the conflict
                # Pass on that it was requeued automatically and to NOT requeue things in that run,
                # otherwise two tickets will requeue each other forever
                if not no_requeue:
                    GitQueue.enqueue_request(
                        GitTaskAction.TEST_PICKME_CONFLICT,
                        pickme,
                        no_requeue=True
                    )

        # If there were no conflicts, don't update the request
        if len(conflict_pickmes) == 0:
            return False, None

        updated_tags = add_to_tags_str(req['tags'], 'conflict-pickme')
        formatted_conflicts = "";
        for broken_pickme, git_out, git_err in conflict_pickmes:
            pickme_details = cls._get_request(broken_pickme)
            formatted_pickme_err = (
            """<strong>Conflict with <a href=\"/request?id={pickme_id}\">{pickme_name}</a>: </strong><br/>{pickme_out}<br/>{pickme_err}<br/><br/>"""
            ).format(
                pickme_id = broken_pickme,
                pickme_err = git_err,
                pickme_out = git_out,
                pickme_name = pickme_details['title']
            )
            formatted_conflicts += formatted_pickme_err

        updated_values = {
            'tags': updated_tags,
            'conflicts': formatted_conflicts
        }

        updated_request = cls._update_request(req, updated_values)
        if not updated_request:
            raise Exception("Failed to update pickme details")
        else:
            return True, updated_request

    @classmethod
    def _clear_pickme_conflict_details(cls, req):
        """
        Strips the conflict-pickme and conflict-master tags from a pickme, and
        clears the detailed conflict field.

        :param req: Details of pickme request to clear conflict details of
        """
        updated_tags = del_from_tags_str(req['tags'], 'conflict-master')
        updated_tags = del_from_tags_str(updated_tags, 'conflict-pickme')
        updated_values = {
            'tags': updated_tags,
            'conflicts': ''
        }
        updated_request = cls._update_request(req, updated_values)
        if not updated_request:
            raise Exception("Failed to update pickme")

    @classmethod
    def _test_pickme_conflict_master(cls, req, target_branch, repo_path, no_requeue):
        """
        Test whether the pickme given by req can be successfully merged onto
        master.

        If the pickme was merged successfully, it calls _test_pickme_conflict_pickme
        to check the pickme against others in the same push.

        :param req: Details of pickme request to test
        :param target_branch: The name of the test branch to use for testing
        :param repo_path: The location of the repository we are working in
        """

        # Create a test branch following master
        with GitBranchContextManager(target_branch, repo_path):
            # Merge the pickme we are testing onto the test branch
            # If this fails, that means pickme conflicts with master
            try:
                with GitMergeContextManager(target_branch, repo_path, req):
                    # Check for conflicts with other pickmes
                    return cls._test_pickme_conflict_pickme(
                        req,
                        target_branch,
                        repo_path,
                        no_requeue
                    )

            except GitException, e:
                updated_tags = add_to_tags_str(req['tags'], 'conflict-master')
                updated_values = {
                        'tags': updated_tags,
                        'conflicts': "<strong>Conflict with master:</strong><br/> %s" % e.gitout
                    }

                updated_request = cls._update_request(req, updated_values)
                if not updated_request:
                    raise Exception("Failed to update pickme")
                else:
                    return True, updated_request

    @classmethod
    def test_pickme_conflicts(cls, request_id, no_requeue=False):
        """
        Tests for conflicts between a pickme and both master and other pickmes
        in the same push.

        :param request_id: ID number of the pickme to be tested
        :param no_requeue: Whether or not pickmes that this pickme conflicts with
            should be added back into the GitQueue as a test conflict task.
        """

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

        # Clear the pickme's conflict info
        cls._clear_pickme_conflict_details(req)

        # Check for conflicts with master
        conflict, updated_pickme = cls._test_pickme_conflict_master(
            req,
            target_branch,
            repo_path,
            no_requeue
        )
        if conflict:
            if updated_pickme is None:
                raise Exception("Encountered merge conflict but was not passed details")
            cls.pickme_conflict_detected(updated_pickme)
            return

    @classmethod
    def pickme_conflict_detected(cls, updated_request):
        msg = (
        """
        <p>
            PushManager has detected that your pickme contains conflicts with %(conflicts_with)s.
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
            <code>%(revision)s</code><br/>
            <em>(If this is <strong>not</strong> the revision you expected,
            make sure you've pushed your latest version to the correct repo!)</em>
        </p>
        <p>
            %(no_escape_conflicts)s
        </p>
        <p>
            Regards,<br/>
            PushManager
        </p>
        """)
        updated_request.update({
            'conflicts_with': "master" if 'conflict-master' in updated_request['tags'] else "another pickme",
            'conflicts': updated_request['conflicts'].replace('\n', '<br/>'),
            'pushmanager_servername': Settings['main_app']['servername'],
            'pushmanager_port': ':%d' % Settings['main_app']['port'] if Settings['main_app']['port'] != 443 else '',
            'reviewboard_servername': Settings['reviewboard']['servername']
        })
        msg %= EscapedDict(updated_request)
        subject = '[push][conflict] %s - %s' % (updated_request['user'], updated_request['title'])
        user_to_notify = updated_request['user']
        MailQueue.enqueue_user_email([user_to_notify], msg, subject)

        msg = """PushManager has detected that your pickme for %(pickme_name)s contains conflicts with %(conflicts_with)s
            https://%(pushmanager_servername)s%(pushmanager_port)s/request?id=%(pickme_id)s""" % {
            'conflicts_with': "master" if 'conflict-master' in updated_request['tags'] else "another pickme",
            'pickme_name': updated_request['branch'],
            'pickme_id': updated_request['id'],
            'pushmanager_servername': Settings['main_app']['servername'],
            'pushmanager_port': ':%d' % Settings['main_app']['port'] if Settings['main_app']['port'] != 443 else ''
        }
        XMPPQueue.enqueue_user_xmpp([user_to_notify], msg)

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
                    cls.test_pickme_conflicts(task.request_id, **task.kwargs)
                elif task.task_type is GitTaskAction.TEST_ALL_PICKMES:
                    for pickme_id in cls._get_request_ids_in_push(task.request_id):
                        GitQueue.enqueue_request(GitTaskAction.TEST_PICKME_CONFLICT, pickme_id)
                else:
                    logging.error("GitQueue encountered unknown task type %d" % task.task_type)
            except Exception:
                logging.error('THREAD ERROR:', exc_info=True)
            finally:
                cls.request_queue.task_done()

    @classmethod
    def enqueue_request(cls, task_type, request_id, **kwargs):
        if not cls.request_queue:
            logging.error("Attempted to put to nonexistent GitQueue!")
            return
        cls.request_queue.put(GitQueueTask(task_type, request_id, **kwargs))

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
