#!/usr/bin/python

from datetime import datetime, timedelta
import os
import sqlite3
import tempfile
import time

from core import db

def create_temp_db_file():
    fd, db_file_path = tempfile.mkstemp(suffix="pushmanager.db")
    os.close(fd)
    return db_file_path

def get_temp_db_uri(dbfile=None):
    if not dbfile:
        dbfile = create_temp_db_file()
    return "sqlite:///" + dbfile

def make_test_db(dbfile=None):
    if not dbfile:
        dbfile = create_temp_db_file()

    testsql = open(
        os.path.join(
            os.path.dirname(__file__),
            "testdb.sql"
        )
    ).read()
    test_db = sqlite3.connect(dbfile)
    test_db.cursor().executescript(testsql)
    test_db.commit()
    test_db.close()
    return dbfile


class FakeDataMixin(object):
    now = time.time()
    yesterday = time.mktime((datetime.now() - timedelta(days=1)).timetuple())

    push_data = [
        [10, 'OnePush', 'bmetin', 'deploy-1', '', 'abc', 'live', yesterday, now, 'regular', ''],
        [11, 'TwoPush', 'troscoe', 'deploy-2', '', 'def', 'accepting', now, now, 'regular', ''],
        [12, 'RedPush', 'heyjoe', 'deploy-3', '', 'ghi', 'accepting', now, now, 'regular', ''],
        [13, 'BluePush', 'humpty', 'deploy-4', '', 'jkl', 'accepting', now, now, 'regular', ''],
    ]
    push_keys = [
        'id', 'title', 'user', 'branch', 'stageenv', 'revision', 'state',
        'created', 'modified', 'pushtype', 'extra_pings'
    ]

    fake_revision = "0"*40

    request_data = [
        [10, 'keysersoze', 'requested', 'keysersoze', 'usual_fix', '', now, now, 'Fix stuff', 'no comment', 12345, '', fake_revision, ''],
        [11, 'bmetin', 'requested', 'bmetin', 'fix1', '', now, now, 'Fixing more stuff', 'yes comment', 234, '', fake_revision, 'testuser3'],
        [12, 'testuser1', 'requested', 'testuser2', 'fix1', 'search', now, now, 'Fixing1', 'no comment', 123, '', fake_revision, 'testuser3, testuser4'],
        [13, 'testuser2', 'requested', 'testuser2', 'fix2', 'search', now, now, 'Fixing2', 'yes comment', 456, '', fake_revision, 'testuser5'],

    ]
    request_keys = [
        'id', 'user', 'state', 'repo', 'branch', 'tags', 'created', 'modified',
        'title', 'comments', 'reviewid', 'description', 'revision', 'watchers'
    ]

    def on_db_return(self, success, db_results):
        assert success

    def make_push_dict(self, data):
        return dict(zip(self.push_keys, data))

    def make_request_dict(self, data):
        return dict(zip(self.request_keys, data))

    def insert_pushes(self):
        push_queries = []
        for pd in self.push_data:
            push_queries.append(db.push_pushes.insert(self.make_push_dict(pd)))
        db.execute_transaction_cb(push_queries, self.on_db_return)

    def insert_requests(self):
        request_queries = []
        for rd in self.request_data:
            request_queries.append(db.push_requests.insert(self.make_request_dict(rd)))
        db.execute_transaction_cb(request_queries, self.on_db_return)

    def insert_pushcontent(self, requestid, pushid):
        db.execute_cb(
            db.push_pushcontents.insert({'request': requestid, 'push': pushid}),
            self.on_db_return
        )

    def get_push_for_request(self, requestid):
        pushid = [None]
        def on_select_return(success, db_results):
            assert success
            _, pushid[0] = db_results.fetchone()

        # check if we have a push in with request
        first_pushcontent_query = db.push_pushcontents.select(
            db.push_pushcontents.c.request == requestid
        )
        db.execute_cb(first_pushcontent_query, on_select_return)
        return pushid[0]

    def get_pushes(self):
        pushes = [None]
        def on_select_return(success, db_results):
            assert success
            pushes[0] = db_results.fetchall()

        db.execute_cb(db.push_pushes.select(), on_select_return)
        return pushes[0]

    def get_requests(self):
        requests = [None]
        def on_select_return(success, db_results):
            assert success
            requests[0] = db_results.fetchall()

        db.execute_cb(db.push_requests.select(), on_select_return)
        return requests[0]

    def get_requests_by_user(self, user):
        return [req for req in self.get_requests() if req['user'] == user]
