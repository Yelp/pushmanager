# -*- coding: utf-8 -*-
from contextlib import contextmanager
from contextlib import nested
import copy
import os

import mock

from pushmanager.core import db
from pushmanager.core.settings import Settings
from pushmanager.testing.mocksettings import MockedSettings
import pushmanager.core.git
import pushmanager.testing as T

class CoreGitTest(T.TestCase):

    @T.class_setup
    def setup_db(self):
        self.db_file = T.testdb.make_test_db()
        MockedSettings['db_uri'] = T.testdb.get_temp_db_uri(self.db_file)
        MockedSettings['irc'] = {
            "nickname": "pushhamster+test",
            "channel": "pushmanagertest"
        }
        with mock.patch.dict(db.Settings, MockedSettings):
            db.init_db()

    @T.setup
    def setup_fake_request_and_settings(self):
        self.fake_push_mapping = {
            'push': 1,
            'request': 1
        }
        self.fake_push = {
            'id': 1,
            'title': 'Test Push Title',
            'branch': 'test-push-branch',
            'revision': '0000000000000000000000000000000000000000',
            'state': 'accepting',
            'created': 1402098724,
            'modified': 1402098724,
            'pushtype': 'regular'
        }
        self.fake_request = {
            'id': 1,
            'title': 'Test Push Request Title',
            'user': 'testuser',
            'tags': 'super-safe,logs',
            'revision': "0"*40,
            'reviewid': 1,
            'state': 'requested',
            'repo': 'testuser',
            'branch': 'super_safe_fix',
            'comments': 'No comment',
            'description': 'I approve this fix!',
            'conflicts': 'Breaks everything!'
        }
        self.fake_settings = {
          'scheme': 'git',
          'auth': '',
          'port': '',
          'servername': 'example',
          'main_repository': 'main_repository',
          'dev_repositories_dir': 'dev_directory',
          'local_repo_path': '/tmp/repo/',
          'local_mirror': '/tmp/mirror/'
        }

    @T.class_teardown
    def cleanup_db(self):
        db.finalize_db()
        os.unlink(self.db_file)

    @contextmanager
    def mocked_update_request(self, req, duplicate_req=None):
        with nested(
            mock.patch("%s.pushmanager.core.git.time" % __name__),
            mock.patch("%s.pushmanager.core.git.MailQueue" % __name__),
            mock.patch("%s.pushmanager.core.git.webhook_req" % __name__),
            mock.patch(
                "%s.pushmanager.core.git.GitQueue._get_branch_sha_from_repo" % __name__,
                return_value=req['revision']
            ),
            mock.patch(
                "%s.pushmanager.core.git.GitQueue._get_request" % __name__,
                return_value=req
            ),
            mock.patch(
                "%s.pushmanager.core.git.GitQueue._get_request_with_sha" % __name__,
                return_value=duplicate_req
            ),
        ):
            pushmanager.core.git.GitQueue.verify_branch(req['id'])
            yield

    def test_get_repository_uri_basic(self):
        MockedSettings["git"] = self.fake_settings
        with mock.patch.dict(Settings, MockedSettings):
            T.assert_equal(pushmanager.core.git.GitQueue._get_repository_uri("main_repository"),
              "git://example/main_repository")
            T.assert_equal(pushmanager.core.git.GitQueue._get_repository_uri("second_repository"),
              "git://example/dev_directory/second_repository")

    def test_get_repository_uri_with_auth(self):
        MockedSettings["git"] = self.fake_settings
        MockedSettings["git"]["auth"] = "myuser:mypass"
        with mock.patch.dict(Settings, MockedSettings):
            T.assert_equal(pushmanager.core.git.GitQueue._get_repository_uri("main_repository"),
              "git://myuser:mypass@example/main_repository")
            T.assert_equal(pushmanager.core.git.GitQueue._get_repository_uri("second_repository"),
              "git://myuser:mypass@example/dev_directory/second_repository")

    def test_get_repository_uri_with_port(self):
        MockedSettings["git"] = self.fake_settings
        MockedSettings["git"]["port"] = "0"
        with mock.patch.dict(Settings, MockedSettings):
            T.assert_equal(pushmanager.core.git.GitQueue._get_repository_uri("main_repository"),
              "git://example:0/main_repository")
            T.assert_equal(pushmanager.core.git.GitQueue._get_repository_uri("second_repository"),
              "git://example:0/dev_directory/second_repository")

    def test_process_queue_successful(self):
        """Update the request with its sha"""
        with nested(
            mock.patch("%s.pushmanager.core.git.GitQueue.verify_branch_failure" % __name__),
            mock.patch("%s.pushmanager.core.git.GitQueue.verify_branch_successful" % __name__),
            self.mocked_update_request(self.fake_request)
        ):
            # Successful call to update_request should trigger verify_branch_successful
            T.assert_equal(pushmanager.core.git.GitQueue.verify_branch_failure.call_count, 0)
            T.assert_equal(pushmanager.core.git.GitQueue.verify_branch_successful.call_count, 1)

        result = [None]
        def on_db_return(success, db_results):
            assert success, "Database error"
            result[0] = db_results.first()

        request_info_query = db.push_requests.select().where(
            db.push_requests.c.id == self.fake_request['id']
        )
        db.execute_cb(request_info_query, on_db_return)

        T.assert_equal(result[0][5], self.fake_request['revision'])

    def test_process_queue_duplicate(self):
        with nested(
            mock.patch("%s.pushmanager.core.git.GitQueue.verify_branch_failure" % __name__),
            mock.patch("%s.pushmanager.core.git.GitQueue.verify_branch_successful" % __name__),
            # This will fail, stop logging errors
            mock.patch("%s.pushmanager.core.git.logging.error" % __name__),
            mock.patch(
                "%s.pushmanager.core.git.GitQueue._get_request_with_sha" % __name__,
                return_value = {'id': 10, 'state': 'requested'}
            ),
            self.mocked_update_request(self.fake_request, self.fake_request)
        ):
            # GitQueue._get_request_with_sha returning a value means
            # we have a duplicated request. This should trigger a
            # failure
            T.assert_equal(pushmanager.core.git.GitQueue.verify_branch_failure.call_count, 1)
            T.assert_equal(pushmanager.core.git.GitQueue.verify_branch_successful.call_count, 0)

            # Match the error message for duplicate revision. error_msg
            # should be the last item of the first call object's *args list
            # (from mock library).
            T.assert_in(
                "another request with the same revision sha",
                pushmanager.core.git.GitQueue.verify_branch_failure.call_args_list[0][0][-1]
            )

    def test_update_duplicate_request_discarded(self):
        duplicate_req = copy.deepcopy(self.fake_request)
        duplicate_req['state'] = "discarded"
        with nested(
            mock.patch("%s.pushmanager.core.git.GitQueue.verify_branch_failure" % __name__),
            mock.patch("%s.pushmanager.core.git.GitQueue.verify_branch_successful" % __name__),
            self.mocked_update_request(self.fake_request, duplicate_req)
        ):
            T.assert_equal(pushmanager.core.git.GitQueue.verify_branch_failure.call_count, 0)
            T.assert_equal(pushmanager.core.git.GitQueue.verify_branch_successful.call_count, 1)

    def test_verify_branch_successful(self):
        with nested(
            mock.patch("%s.pushmanager.core.git.MailQueue.enqueue_user_email" % __name__),
            mock.patch("%s.pushmanager.core.git.webhook_req" % __name__)
        ):
            pushmanager.core.git.GitQueue.verify_branch_successful(self.fake_request)
            T.assert_equal(pushmanager.core.git.MailQueue.enqueue_user_email.call_count, 1)
            T.assert_equal(pushmanager.core.git.webhook_req.call_count, 3)

    def test_verify_branch_failure(self):
        with nested(
            mock.patch("%s.pushmanager.core.git.MailQueue.enqueue_user_email" % __name__),
            mock.patch("%s.pushmanager.core.git.webhook_req" % __name__),
            mock.patch("%s.pushmanager.core.git.logging.error" % __name__),
        ):
            pushmanager.core.git.GitQueue.verify_branch_failure(self.fake_request, "fake failure")
            T.assert_equal(pushmanager.core.git.MailQueue.enqueue_user_email.call_count, 1)

    def test_verify_branch_excluded_from_git_verification(self):
        for tag in pushmanager.core.git.GitQueue.EXCLUDE_FROM_GIT_VERIFICATION:
            req = copy.deepcopy(self.fake_request)
            req['branch'] = None
            req['tags'] = tag

            with nested(
                mock.patch("%s.pushmanager.core.git.GitQueue.verify_branch_failure" % __name__),
                mock.patch("%s.pushmanager.core.git.GitQueue.verify_branch_successful" % __name__),
                self.mocked_update_request(req)
            ):
                T.assert_equal(pushmanager.core.git.GitQueue.verify_branch_failure.call_count, 0)
                T.assert_equal(pushmanager.core.git.GitQueue.verify_branch_successful.call_count, 0)

    class GitCommandFailMock(object):
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        def run(self):
            raise pushmanager.core.git.GitException(
                "GitException: git %s " % ' '.join(self.args),
                gitrc = 1,
                giterr = "stderr",
                gitout = "stdout",
                gitcwd = self.kwargs['cwd'] if 'cwd' in self.kwargs else None
            )

    class GitCommandOKMock(object):
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        def run(self):
            return 0, "stdout", "stderr"

    @mock.patch('pushmanager.core.git.GitCommand', GitCommandFailMock)
    def test_branch_ctx_manager_error(self):
        with T.assert_raises(pushmanager.core.git.GitException):
            with pushmanager.core.git.GitBranchContextManager("name_of_test_branch", "path_to_master_repo"):
                pass



    @mock.patch('pushmanager.core.git.GitCommand', GitCommandOKMock)
    def test_branch_ctx_manager_clean(self):
        with mock.patch('pushmanager.core.git.GitCommand') as GCMock:
            gitcmd_instance = GCMock.return_value()
            gitcmd_instance.run.return_value = (0, "", "")

            with pushmanager.core.git.GitBranchContextManager("name_of_test_branch", "path_to_master_repo"):
                pass

    class GitCommandFailOnCommitMock(object):
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        def run(self):
            if self.args[0] is "commit":
                raise pushmanager.core.git.GitException(
                "GitException: git %s " % ' '.join(self.args),
                gitrc = 1,
                giterr = "stderr",
                gitout = "stdout",
                gitcwd = self.kwargs['cwd'] if 'cwd' in self.kwargs else None
            )
            return 0, "some_hash some_branch", ""

    @mock.patch('pushmanager.core.git.GitCommand', GitCommandFailOnCommitMock)
    def test_merge_ctx_manager(self):
        with mock.patch('pushmanager.core.git.git_reset_to_ref', autospec=True) as self.mock_reset_ref:
            with T.assert_raises(pushmanager.core.git.GitException):
                with pushmanager.core.git.GitMergeContextManager(
                    "name_of_test_branch",
                    "path_to_master_repo",
                    {
                        'title':'Test Branch',
                        'user':'infradev',
                        'branch':'test_branch'
                    }
                ):
                    pass
        T.assert_equal(self.mock_reset_ref.call_count, 1)

    @mock.patch("os.path.isdir", lambda x: True)
    def test_create_or_update_local_repo_reference(self):
        with mock.patch('pushmanager.core.git.GitCommand') as GCMock:
            MockedSettings["git"] = self.fake_settings
            MockedSettings["git"]['use_local_mirror'] = True
            with mock.patch.dict(Settings, MockedSettings):
                gitcmd_instance = GCMock.return_value()
                gitcmd_instance.run.return_value = (0, "", "")
                pushmanager.core.git.GitQueue.create_or_update_local_repo(
                    self.fake_settings['main_repository'], "test-branch"
                )

    @mock.patch("pushmanager.core.git.GitQueue._get_request")
    @mock.patch("pushmanager.core.git.GitQueue._get_push_for_request")
    @mock.patch("pushmanager.core.git.GitQueue._clear_pickme_conflict_details")
    @mock.patch("pushmanager.core.git.GitQueue._test_pickme_conflict_master")
    def test_pickme_conflict_logic(self, mock_conflict_master, mock_clear_conflcits, mock_get_push, mock_get_req):
        mock_get_req.return_value = copy.deepcopy(self.fake_request)
        mock_get_push.return_value = copy.deepcopy(self.fake_push_mapping)
        mock_conflict_master.return_value = False, None
        with mock.patch('pushmanager.core.git.GitCommand'):
            pushmanager.core.git.GitQueue.test_pickme_conflicts("1")

    @mock.patch("pushmanager.core.xmppclient.XMPPQueue.enqueue_user_xmpp")
    @mock.patch("pushmanager.core.mail.MailQueue.enqueue_user_email")
    @mock.patch("pushmanager.core.git.GitQueue._get_request")
    @mock.patch("pushmanager.core.git.GitQueue._get_push_for_request")
    @mock.patch("pushmanager.core.git.GitQueue._clear_pickme_conflict_details")
    @mock.patch("pushmanager.core.git.GitQueue._test_pickme_conflict_master")
    def test_pickme_conflict_err_handling(self, mock_conflict_master, mock_clear_conflcits, mock_get_push, mock_get_req, mock_mail, mock_xmpp):
        mock_get_req.return_value = copy.deepcopy(self.fake_request)
        mock_get_push.return_value = copy.deepcopy(self.fake_push_mapping)
        mock_conflict_master.return_value = True, copy.deepcopy(self.fake_request)
        with mock.patch('pushmanager.core.git.GitCommand'):
            pushmanager.core.git.GitQueue.test_pickme_conflicts("1")

    @mock.patch('pushmanager.core.git.GitCommand', GitCommandFailMock)
    @mock.patch("pushmanager.core.mail.MailQueue.enqueue_user_email")
    @mock.patch("pushmanager.core.git.GitQueue.create_or_update_local_repo")
    def test_get_sha_from_repo_fail(self, mock_update_repo, mock_mail):
        pushmanager.core.git.GitQueue._get_branch_sha_from_repo(copy.deepcopy(self.fake_request))
        T.assert_equal(mock_update_repo.call_count, 1)
        T.assert_equal(mock_mail.call_count, 1)

    @mock.patch('pushmanager.core.git.GitCommand')
    @mock.patch("pushmanager.core.mail.MailQueue.enqueue_user_email")
    @mock.patch("pushmanager.core.git.GitQueue.create_or_update_local_repo")
    def test_get_sha_from_repo_ok(self, mock_update_repo, mock_mail, mock_gc):
        mock_gc.return_value.run.return_value = (0, "e3a492e626a9706f6cde7bf81ae4ce9d18430f4d	refs/heads/master", "")
        pushmanager.core.git.GitQueue._get_branch_sha_from_repo(copy.deepcopy(self.fake_request))
        T.assert_equal(mock_update_repo.call_count, 1)
        T.assert_equal(mock_mail.call_count, 1)


    class FailureMergeContext(object):
        def __init__(self, *args):
            self.args = args

        def __enter__(self):
            raise pushmanager.core.git.GitException(
                "GitException",
                gitrc = 1,
                giterr = "stderr",
                gitout = "stdout",
                gitcwd = None
            )

        def __exit__(self, *args):
            pass

    @mock.patch("pushmanager.core.git.GitQueue._update_request")
    @mock.patch("pushmanager.core.git.GitQueue._get_push_for_request")
    @mock.patch("pushmanager.core.git.GitQueue._get_request_ids_in_push")
    @mock.patch("pushmanager.core.git.GitQueue._get_request")
    @mock.patch("pushmanager.core.git.GitMergeContextManager", FailureMergeContext)
    def test_pickme_breaks_pickme(self, m_get_request, m_ids_in_push, m_push_for_req, m_update_req):
        m_push_for_req.return_value = copy.deepcopy(self.fake_push_mapping)
        m_ids_in_push.return_value = ['1', '2']
        m_get_request.return_value = copy.deepcopy(self.fake_request)

        (conflict, _) = pushmanager.core.git.GitQueue._test_pickme_conflict_pickme(
            copy.deepcopy(self.fake_request),
            "dummy_branch",
            "repo_path",
            True
        )

        T.assert_equal(conflict, True)
        conflict_information = m_update_req.call_args[0][1]
        print conflict_information
        T.assert_equal('conflict-pickme' in conflict_information['tags'], True)

    @mock.patch("pushmanager.core.git.GitMergeContextManager", FailureMergeContext)
    @mock.patch("pushmanager.core.git.GitQueue._update_request")
    @mock.patch("pushmanager.core.git.GitBranchContextManager")
    @mock.patch("pushmanager.core.git.GitQueue._test_pickme_conflict_pickme")
    def test_pickme_breaks_master(self, m_pickme_test, mBranchManager, m_update_req):
        (conflict, _) = pushmanager.core.git.GitQueue._test_pickme_conflict_master(
            copy.deepcopy(self.fake_request),
            "dummy_branch",
            "repo_path",
            True
        )
        T.assert_equal(conflict, True)
        conflict_information = m_update_req.call_args[0][1]
        print conflict_information
        T.assert_equal('conflict-master' in conflict_information['tags'], True)
