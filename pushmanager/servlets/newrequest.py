import re
import time

import sqlalchemy as SA

import pushmanager.core.db as db
import pushmanager.core.util
from pushmanager.core.git import GitQueue
from pushmanager.servlets.checklist import checklist_reminders
from pushmanager.core.git import GitTaskAction
from pushmanager.core.requesthandler import RequestHandler


TAGS_RE = re.compile(r'[a-zA-Z0-9_-]+')
CONFLICT_TAGS = frozenset(('conflict-pickme', 'conflict-master'))


class NewRequestServlet(RequestHandler):

    def _arg(self, key):
        return pushmanager.core.util.get_str_arg(self.request, key, '')

    def post(self):
        if not self.current_user:
            return self.send_error(403)
        self.requestid = self._arg('request-id')
        self.tag_list = [
            x
            for x in TAGS_RE.findall(self._arg('request-tags'))
            if x and x not in CONFLICT_TAGS
        ]

        reviewid = self._arg('request-review')
        if reviewid:
            try:
                reviewid = int(reviewid)
            except (ValueError, TypeError):
                return self.send_error(500)

        watchers = ','.join(map(str.strip, self._arg('request-watchers').split(',')))

        if self.requestid != '':
            self.requestid = int(self.requestid)

            updated_values = {
                    'title': self._arg('request-title'),
                    'tags': ','.join(self.tag_list),
                    'reviewid': reviewid or None,
                    'repo': self._arg('request-repo').strip(),
                    'branch': self._arg('request-branch').strip(),
                    'comments': self._arg('request-comments'),
                    'description': self._arg('request-description'),
                    'watchers': watchers,
                    'modified': time.time(),
                    'revision': '0'*40,
            }

            if len(self._arg('request-takeover')):
                updated_values.update({'user': self.current_user})
                self.request_user = self.current_user
            else:
                self.request_user = self._arg('request-user')

            query = db.push_requests.update().where(
                    db.push_requests.c.id == self.requestid
                ).values(updated_values)
        else:
            query = db.push_requests.insert({
                'title': self._arg('request-title'),
                'user': self.current_user,
                'tags': ','.join(self.tag_list),
                'reviewid': self._arg('request-review') or None,
                'repo': self._arg('request-repo').strip(),
                'branch': self._arg('request-branch').strip(),
                'comments': self._arg('request-comments'),
                'description': self._arg('request-description'),
                'watchers': watchers,
                'created': time.time(),
                'modified': time.time(),
                'state': 'requested',
                'revision': '0'*40,
                })
            self.request_user = self.current_user

        db.execute_cb(query, self.on_request_upsert_complete)

    def on_request_upsert_complete(self, success, db_results):
        self.check_db_results(success, db_results)

        if not self.requestid:
            self.requestid = db_results.lastrowid

        query = db.push_checklist.select().where(db.push_checklist.c.request == self.requestid)
        db.execute_cb(query, self.on_existing_checklist_retrieved)

    def on_existing_checklist_retrieved(self, success, db_results):
        if not success or not db_results:
            # We should have the new request in db by this time.
            return self.send_error(500)

        existing_checklist_types = set(x['type'] for x in db_results.fetchall())
        queries = []

        necessary_checklist_types = set()

        if 'pushplans' in self.tag_list:
            necessary_checklist_types.add('pushplans')
            necessary_checklist_types.add('pushplans-cleanup')
        if 'search-backend' in self.tag_list:
            necessary_checklist_types.add('search')
            necessary_checklist_types.add('search-cleanup')
        if 'hoods' in self.tag_list:
            necessary_checklist_types.add('hoods')
            necessary_checklist_types.add('hoods-cleanup')

        types_to_add = necessary_checklist_types - existing_checklist_types
        types_to_remove = existing_checklist_types - necessary_checklist_types

        for type_ in types_to_add:
            for target in checklist_reminders[type_].keys():
                queries.append(db.push_checklist.insert().values(
                    {'request': self.requestid, 'type': type_, 'target': target}
                ))

        if types_to_remove:
            queries.append(db.push_checklist.delete().where(SA.and_(
                db.push_checklist.c.request == self.requestid,
                db.push_checklist.c.type.in_(types_to_remove),
            )))

        db.execute_transaction_cb(queries, self.on_checklist_upsert_complete)

    def on_checklist_upsert_complete(self, success, db_results):
        if not success:
            return self.send_error(500)

        if self.requestid:
            GitQueue.enqueue_request(GitTaskAction.VERIFY_BRANCH, self.requestid)

            # Check if the request is already pickme'd for a push, and if
            # so also enqueue it to be checked for conflicts.
            request_push_id = GitQueue._get_push_for_request(self.requestid)
            if request_push_id:
                GitQueue.enqueue_request(GitTaskAction.TEST_PICKME_CONFLICT, self.requestid)

        return self.redirect("/requests?user=%s" % self.request_user)
