import sqlalchemy as SA
import time
import re

import core.db as db
from core.git import GitQueue
from core.requesthandler import RequestHandler
import core.util

TAGS_RE = re.compile(r'[a-zA-Z0-9_-]+')


class NewRequestServlet(RequestHandler):

    def _arg(self, key):
        return core.util.get_str_arg(self.request, key, '')

    def post(self):
        if not self.current_user:
            return self.send_error(403)
        self.requestid = self._arg('request-id')
        self.tag_list = [x for x in TAGS_RE.findall(self._arg('request-tags')) if x]

        reviewid = self._arg('request-review')
        if reviewid:
            try:
                reviewid = int(reviewid)
            except (ValueError, TypeError):
                return self.send_error(500)

        if self.requestid != '':
            self.requestid = int(self.requestid)
            query = db.push_requests.update().where(
                    db.push_requests.c.id == self.requestid
                ).values({
                    'title': self._arg('request-title'),
                    'user': self.current_user,
                    'tags': ','.join(self.tag_list),
                    'reviewid': reviewid or None,
                    'repo': self._arg('request-repo'),
                    'branch': self._arg('request-branch'),
                    'comments': self._arg('request-comments'),
                    'description': self._arg('request-description'),
                    'modified': time.time(),
                    'revision': '0'*40,
                })
        else:
            query = db.push_requests.insert({
                'title': self._arg('request-title'),
                'user': self.current_user,
                'tags': ','.join(self.tag_list),
                'reviewid': self._arg('request-review') or None,
                'repo': self._arg('request-repo'),
                'branch': self._arg('request-branch'),
                'comments': self._arg('request-comments'),
                'description': self._arg('request-description'),
                'created': time.time(),
                'modified': time.time(),
                'state': 'requested',
                'revision': '0'*40,
                })

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
        if 'search-backend' in self.tag_list:
            necessary_checklist_types.add('search')
        if 'hoods' in self.tag_list:
            necessary_checklist_types.add('hoods')

        types_to_add = necessary_checklist_types - existing_checklist_types
        types_to_remove = existing_checklist_types - necessary_checklist_types

        # Different types of checklist items need to happen at different points.
        targets_by_type = {
            'pushplans' : ('stage', 'prod'),
            'search' : ('post-stage', 'prod', 'post-prod', 'post-verify'),
            'hoods' : ('stage', 'post-stage', 'prod'),
            # We need to append checklist items to clean up after
            # push plans & search checklist items.
            'pushplans-cleanup' : ('post-verify-stage',),
            'search-cleanup': ('post-verify-prod',),
            'hoods-cleanup' : ('post-verify-stage',),
        }

        for type_ in types_to_add:
            for target in targets_by_type[type_]:
                queries.append(db.push_checklist.insert().values(
                    {'request': self.requestid, 'type': type_, 'target': target}
                ))

            cleanup_type = "%s-cleanup" % type_
            for target in targets_by_type[cleanup_type]:
                queries.append(db.push_checklist.insert().values(
                    {'request': self.requestid, 'type': cleanup_type, 'target': target}
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
            GitQueue.enqueue_request(self.requestid)

        return self.redirect("/requests?user=%s" % self.current_user)
