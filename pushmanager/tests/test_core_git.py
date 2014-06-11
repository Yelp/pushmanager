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
        }
        self.fake_settings = {
          'scheme': 'git',
          'auth': '',
          'port': '',
          'servername': 'example',
          'main_repository': 'main_repository',
          'dev_repositories_dir': 'dev_directory'
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
            return 1, "", ""

    @mock.patch('pushmanager.core.git.GitCommand', GitCommandFailMock)
    def test_branch_ctx_manager(self):
        with T.assert_raises(pushmanager.core.git.GitException):
            with pushmanager.core.git.GitBranchContextManager("name_of_test_branch", "path_to_master_repo"):
                pass

    class GitCommandFailOnCommitMock(object):
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        def run(self):
            if self.args[0] is "commit":
                return 1, "", ""
            else :
                return 0, "", ""

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
