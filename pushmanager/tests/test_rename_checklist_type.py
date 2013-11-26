# -*- coding: utf-8 -*-
from functools import partial
import os

from mock import patch

from core import db
from tools import rename_checklist_type
from pushmanager.testing.mocksettings import MockedSettings
from pushmanager.testing.testdb import FakeDataMixin
import pushmanager.testing as T


class RenameTagTest(T.TestCase, FakeDataMixin):

    checklist_keys = [ 'id', 'request', 'type', 'complete', 'target']

    checklist_data = [
        [1, 0, 'search', 0, 'stage'],
        [2, 0, 'search', 0, 'prod'],
        [3, 0, 'search-cleanup', 0, 'post-stage-verify'],
        [4, 0, 'pushplans', 0, 'stage'],
        [5, 0, 'pushplans-cleanup', 0, 'prod']
    ]

    @T.setup_teardown
    def setup_db(self):
        self.db_file_path = T.testdb.create_temp_db_file()
        MockedSettings['db_uri'] = T.testdb.get_temp_db_uri(self.db_file_path)
        with patch.dict(db.Settings, MockedSettings):
            db.init_db()
            self.insert_checklists()
            yield
            db.finalize_db()
            os.unlink(self.db_file_path)

    def check_db_results(self, success, db_results):
        if not success:
            raise db.DatabaseError()

    def verify_database_state(self, data, success, db_results):
        self.check_db_results(success, db_results)

        # id, push, *type*, status, target
        data_types = [d[2] for d in data]
        # id, push, *type*, status, target
        types = [result[2] for result in db_results.fetchall()]

        T.assert_sorted_equal(data_types, types)

    def verify_type_rename(self, oldtype, newtype, success, db_results):
        self.check_db_results(success, db_results)

        # id, push, *type*, status, target
        types = [result[2] for result in db_results.fetchall()]

        T.assert_not_in(oldtype, types)
        T.assert_not_in('%s-cleanup' % oldtype, types)
        T.assert_in('%s' % newtype, types)
        T.assert_in('%s-cleanup' % newtype, types)

    def make_checklist_dict(self, data):
        return dict(zip(self.checklist_keys, data))

    def insert_checklists(self):
        checklist_queries = []
        for cl in self.checklist_data:
            checklist_queries.append(db.push_checklist.insert(self.make_checklist_dict(cl)))
        db.execute_transaction_cb(checklist_queries, self.on_db_return)

    @patch('tools.rename_checklist_type.convert_checklist')
    @patch('optparse.OptionParser.error')
    @patch('optparse.OptionParser.parse_args', return_value=[None, []])
    def test_main_noargs(self, parser, error, convert_checklist):
        rename_checklist_type.main()
        T.assert_equal(False, convert_checklist.called)
        error.assert_called_once_with('Incorrect number of arguments')

    @patch('tools.rename_checklist_type.convert_checklist')
    @patch('optparse.OptionParser.error')
    @patch('optparse.OptionParser.parse_args',
            return_value=[None, ['oldtag', 'newtag']])
    def test_main_twoargs(self, parser, error, convert_checklist):
        parser.return_value=[None, ['oldtag', 'newtag']]
        rename_checklist_type.main()
        convert_checklist.assert_called_once_with('oldtag', 'newtag')
        T.assert_equal(False, error.called)

    def test_convert_cleanup_type(self):
        rename_checklist_type.convert_checklist('search', 'not_search')
        cb = partial(self.verify_type_rename, 'search', 'not_search')
        db.execute_cb(db.push_checklist.select(), cb)

    def test_convert_notype(self):
        rename_checklist_type.convert_checklist('nonexistent', 'random')
        cb = partial(self.verify_database_state, self.checklist_data)
        db.execute_cb(db.push_checklist.select(), cb)



if __name__ == '__main__':
    T.run()
