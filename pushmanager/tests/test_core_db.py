#!/usr/bin/env python

import os

from sqlalchemy.schema import Column
from sqlalchemy.schema import Table
from sqlalchemy.sql.compiler import SQLCompiler
from sqlalchemy.types import Integer
import mock
import sqlalchemy as SA

from core import db
import pushmanager.testing as T

class CoreDBTest(T.TestCase, T.FakeDataMixin):

    @T.class_setup
    def setup_db_settings(self):
        self.db_file_path = T.testdb.create_temp_db_file()
        T.MockedSettings['db_uri'] = T.testdb.get_temp_db_uri(self.db_file_path)
        with mock.patch.dict(db.Settings, T.MockedSettings):
            db.init_db()
            self.populate_database()

    @T.class_teardown
    def cleanup_database(self):
        db.finalize_db()
        os.unlink(self.db_file_path)

    def populate_database(self):
        self.insert_pushes()
        self.insert_requests()
        self.insert_pushcontent(1, 1)

    def test_init_db(self):
        assert isinstance(db.push_checklist, SA.schema.Table)
        assert isinstance(db.push_requests, SA.schema.Table)
        assert isinstance(db.push_plans, SA.schema.Table)
        assert isinstance(db.push_pushes, SA.schema.Table)
        assert isinstance(db.push_pushcontents, SA.schema.Table)
        assert isinstance(db.push_removals, SA.schema.Table)

    def test_database_populated(self):
        T.assert_equal(self.get_push_for_request(1), 1)

        pushes = self.get_pushes()
        first_push = self.make_push_dict(self.push_data[0])
        T.assert_equal(pushes[0].title, first_push['title'])

    def test_transaction_with_successful_condition(self):
        def on_return(success, _):
            assert success

        requestid = 1

        db.execute_transaction_cb(
            [db.push_pushcontents.insert({'request': 2, 'push': 2})],
            on_return,
            condition = (
                db.push_pushcontents.select(
                    db.push_pushcontents.c.request == requestid
                ),
                lambda results: results.fetchone().request == requestid
            )
        )

    def test_transaction_with_unsuccessful_condition(self):
        def on_return(success, _):
            # Transaction should fail since the condition will not be
            # successful
            T.assert_equal(success, False)

        # This will fail better not log errors
        with mock.patch("%s.db.logging.error" % __name__):
            db.execute_transaction_cb(
                [db.push_pushcontents.insert({'request': 2, 'push': 2})],
                on_return,
                condition = (
                    # Just a phony query that we don't really care about
                    db.push_pushcontents.select(),
                    lambda results: False
                )
            )

class InsertIgnoreTestCase(T.TestCase):

    table = Table('faketable', SA.MetaData(), Column('a', Integer), Column('b', Integer))
    statement = db.InsertIgnore(table, ({'a': 0, 'b': 1}))

    def assert_ignore_clause(self, scheme, expected):
        dialect = SA.create_engine(scheme + ':///').dialect
        compiler = SQLCompiler(dialect=dialect, statement=self.statement)

        T.assert_equal(str(compiler), expected)

    def test_insert_ignore_mysql(self):
        expected = 'INSERT IGNORE INTO faketable (a, b) VALUES (%s, %s)'
        self.assert_ignore_clause('mysql', expected)

    def test_insert_ignore_sqlite(self):
        expected = 'INSERT OR IGNORE INTO faketable (a, b) VALUES (?, ?)'
        self.assert_ignore_clause('sqlite', expected)
