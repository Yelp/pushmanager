# -*- coding: utf-8 -*-
from contextlib import contextmanager
from contextlib import nested
import copy
import os

import mock

from core import db
from core.settings import Settings
import core.git
import testing as T

class CoreGitTest(T.TestCase):

    @T.class_setup
    def setup_db(self):
        self.db_file = T.make_test_db()
        T.MockedSettings['db_uri'] = T.get_temp_db_uri(self.db_file)
        T.MockedSettings['irc'] = {
            "nickname": "pushhamster+test",
            "channel": "pushmanagertest"
        }
        with mock.patch.dict(db.Settings, T.MockedSettings):
            db.init_db()

    @T.setup
    def setup_fake_request(self):
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

    @T.class_teardown
    def cleanup_db(self):
        db.finalize_db()
        os.unlink(self.db_file)

    @contextmanager
    def mocked_update_request(self, req, duplicate_req=None):
        with nested(
            mock.patch("%s.core.git.time" % __name__),
            mock.patch("%s.core.git.MailQueue" % __name__),
            mock.patch("%s.core.git.webhook_req" % __name__),
            mock.patch(
                "%s.core.git.GitQueue._get_branch_sha_from_repo" % __name__,
                return_value=req['revision']
            ),
            mock.patch(
                "%s.core.git.GitQueue._get_request" % __name__,
                return_value=req
            ),
            mock.patch(
                "%s.core.git.GitQueue._get_request_with_sha" % __name__,
                return_value=duplicate_req
            ),
        ):
            core.git.GitQueue.update_request(req['id'])
            yield

    def test_get_repository_uri(self):
        T.MockedSettings["git"] = {
          "scheme": "git",
          "auth": "",
          "port": "",
          "servername": "example",
          "main_repository": "main_repository", 
          "dev_repositories_dir": "dev_directory"
        }
	with mock.patch.dict(Settings, T.MockedSettings):
            T.assert_equal(core.git.GitQueue._get_repository_uri("main_repository"),
              "git://example/main_repository")
            T.assert_equal(core.git.GitQueue._get_repository_uri("second_repository"),
              "git://example/dev_directory/second_repository")

            T.MockedSettings["git"]["auth"] = "myuser:mypass"
            T.assert_equal(core.git.GitQueue._get_repository_uri("main_repository"),
              "git://myuser:mypass@example/main_repository")
            T.assert_equal(core.git.GitQueue._get_repository_uri("second_repository"),
              "git://myuser:mypass@example/dev_directory/second_repository")

            T.MockedSettings["git"]["port"] = "0"
            T.assert_equal(core.git.GitQueue._get_repository_uri("main_repository"),
              "git://myuser:mypass@example:0/main_repository")
            T.assert_equal(core.git.GitQueue._get_repository_uri("second_repository"),
              "git://myuser:mypass@example:0/dev_directory/second_repository")
            

    def test_process_queue_successful(self):
        """Update the request with its sha"""
        with nested(
            mock.patch("%s.core.git.GitQueue.update_request_failure" % __name__),
            mock.patch("%s.core.git.GitQueue.update_request_successful" % __name__),
            self.mocked_update_request(self.fake_request)
        ):
            # Successful call to update_request should trigger update_request_successful
            T.assert_equal(core.git.GitQueue.update_request_failure.call_count, 0)
            T.assert_equal(core.git.GitQueue.update_request_successful.call_count, 1)

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
            mock.patch("%s.core.git.GitQueue.update_request_failure" % __name__),
            mock.patch("%s.core.git.GitQueue.update_request_successful" % __name__),
            # This will fail, stop logging errors
            mock.patch("%s.core.git.logging.error" % __name__),
            mock.patch(
                "%s.core.git.GitQueue._get_request_with_sha" % __name__,
                return_value = {'id': 10, 'state': 'requested'}
            ),
            self.mocked_update_request(self.fake_request, self.fake_request)
        ):
            # GitQueue._get_request_with_sha returning a value means
            # we have a duplicated request. This should trigger a
            # failure
            T.assert_equal(core.git.GitQueue.update_request_failure.call_count, 1)
            T.assert_equal(core.git.GitQueue.update_request_successful.call_count, 0)

            # Match the error message for duplicate revision. error_msg
            # should be the last item of the first call object's *args list
            # (from mock library).
            T.assert_in(
                "another request with the same revision sha",
                core.git.GitQueue.update_request_failure.call_args_list[0][0][-1]
            )

    def test_update_duplicate_request_discarded(self):
        duplicate_req = copy.deepcopy(self.fake_request)
        duplicate_req['state'] = "discarded"
        with nested(
            mock.patch("%s.core.git.GitQueue.update_request_failure" % __name__),
            mock.patch("%s.core.git.GitQueue.update_request_successful" % __name__),
            self.mocked_update_request(self.fake_request, duplicate_req)
        ):
            T.assert_equal(core.git.GitQueue.update_request_failure.call_count, 0)
            T.assert_equal(core.git.GitQueue.update_request_successful.call_count, 1)

    def test_update_request_successful(self):
        with nested(
            mock.patch("%s.core.git.MailQueue.enqueue_user_email" % __name__),
            mock.patch("%s.core.git.webhook_req" % __name__)
        ):
            core.git.GitQueue.update_request_successful(self.fake_request)
            T.assert_equal(core.git.MailQueue.enqueue_user_email.call_count, 1)
            T.assert_equal(core.git.webhook_req.call_count, 3)

    def test_update_request_failure(self):
        with nested(
            mock.patch("%s.core.git.MailQueue.enqueue_user_email" % __name__),
            mock.patch("%s.core.git.webhook_req" % __name__),
            mock.patch("%s.core.git.logging.error" % __name__),
        ):
            core.git.GitQueue.update_request_failure(self.fake_request, "fake failure")
            T.assert_equal(core.git.MailQueue.enqueue_user_email.call_count, 1)

    def test_update_request_excluded_from_git_verification(self):
        for tag in core.git.GitQueue.EXCLUDE_FROM_GIT_VERIFICATION:
            req = copy.deepcopy(self.fake_request)
            req['branch'] = None
            req['tags'] = tag

            with nested(
                mock.patch("%s.core.git.GitQueue.update_request_failure" % __name__),
                mock.patch("%s.core.git.GitQueue.update_request_successful" % __name__),
                self.mocked_update_request(req)
            ):
                T.assert_equal(core.git.GitQueue.update_request_failure.call_count, 0)
                T.assert_equal(core.git.GitQueue.update_request_successful.call_count, 0)
