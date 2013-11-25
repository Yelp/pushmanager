# -*- coding: utf-8 -*-
from functools import partial
import os

from mock import patch

from core import db
from tools import rename_tag
import pushmanager.testing as T


class RenameTagTest(T.TestCase, FakeDataMixin):

    @T.setup_teardown
    def setup_db(self):
        self.db_file_path = T.testdb.create_temp_db_file()
        MockedSettings['db_uri'] = T.testdb.get_temp_db_uri(self.db_file_path)
        with patch.dict(db.Settings, MockedSettings):
            db.init_db()
            self.insert_requests()
            yield
            db.finalize_db()
            os.unlink(self.db_file_path)

    def check_db_results(self, success, db_results):
        if not success:
            raise db.DatabaseError()

    def verify_database_state(self, data, success, db_results):
        self.check_db_results(success, db_results)

        # id, user, state, repo, branch, *tags*, created, modified, etc...
        data_tags = [d[5] for d in data]
        #id, user, state, repo, branch, revision, *tags*, created, etc...
        tags = [result[6] for result in db_results.fetchall()]

        T.assert_sorted_equal(data_tags, tags)

    def verify_tag_rename(self, oldtag, newtag, success, db_results):
        self.check_db_results(success, db_results)

        #id, user, state, repo, branch, revision, *tags*, created, etc...
        tags = [result[6] for result in db_results.fetchall()]

        T.assert_not_in(oldtag, tags)
        T.assert_in(newtag, tags)

    @patch('tools.rename_tag.convert_tag')
    @patch('optparse.OptionParser.error')
    @patch('optparse.OptionParser.parse_args', return_value=[None, []])
    def test_main_noargs(self, parser, error, convert_tag):
        rename_tag.main()
        T.assert_equal(False, convert_tag.called)
        error.assert_called_once_with('Incorrect number of arguments')

    @patch('tools.rename_tag.convert_tag')
    @patch('optparse.OptionParser.error')
    @patch('optparse.OptionParser.parse_args',
            return_value=[None, ['oldtag', 'newtag']])
    def test_main_twoargs(self, parser, error, convert_tag):
        parser.return_value=[None, ['oldtag', 'newtag']]
        rename_tag.main()
        convert_tag.assert_called_once_with('oldtag', 'newtag')
        T.assert_equal(False, error.called)

    def test_convert_tag(self):
        rename_tag.convert_tag('search', 'not_search')
        cb = partial(self.verify_tag_rename, 'search', 'not_search')
        db.execute_cb(db.push_requests.select(), cb)

    def test_convert_notag(self):
        rename_tag.convert_tag('nonexistent', 'random')
        cb = partial(self.verify_database_state, self.request_data)
        db.execute_cb(db.push_requests.select(), cb)


if __name__ == '__main__':
    T.run()
