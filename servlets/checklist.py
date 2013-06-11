from collections import defaultdict

import sqlalchemy as SA

import core.db as db
from core.requesthandler import RequestHandler
import core.util


checklist_reminders = {
    'pushplans': dict((target, 'Push plans for %(pushee)s') for target in ('stage', 'prod')),
    'search': {
        'post-stage': 'Restart stage search for %(pushee)s',
        'prod': 'Disable index distribution for %(pushee)s',
        'post-prod': 'Flip prod search for %(pushee)s',
        'post-verify': 'Flip dev search for %(pushee)s',
    },
    'hoods': {
        'stage': 'Notify %(pushee)s to deploy Geoservices to stage.',
        'post-stage': 'Ask Search to force index distribution on stage for %(pushee)s',
        'prod': 'Notify %(pushee)s to deploy Geoservices to prod.',
    },
    'pushplans-cleanup': {
        'post-verify-stage': 'Run push plans on other stages for %(pushee)s',
    },
    'search-cleanup': {
        'post-verify-prod': 'Re-enable index distribution in prod for %(pushee)s',
    },
    'hoods-cleanup': {
        'post-verify-stage': 'Notify %(pushee)s to deploy Geoservices to other stages and dev',
    },
}


class ChecklistServlet(RequestHandler):

    def get(self):
        if not self.current_user:
            return self.send_error(403)
        self.pushid = core.util.get_int_arg(self.request, 'id')
        self.pushmaster = core.util.get_int_arg(self.request, 'pushmaster')

        c = db.push_checklist.c
        r = db.push_requests.c

        query = SA.select([
                c.target, c.type, c.complete, c.id, c.request,
                r.title, r.repo, r.branch, r.user,
            ]).where(SA.and_(
                r.id == c.request,
                r.state != 'pickme',
                c.request == db.push_pushcontents.c.request,
                db.push_pushcontents.c.push == self.pushid,
            ))

        db.execute_cb(query, self.on_db_complete)

    post=get

    def on_db_complete(self, success, db_results):
        if not success or db_results is None:
            return self.send_error(500)

        items_by_target = {}
        for item in db_results:
            items_by_target.setdefault(item['target'], []).append(item)

        self.render(
            "checklist.html",
            pushmaster=self.pushmaster,
            items_by_target=self.__dedup_search_list(items_by_target),
            item_count=db_results.rowcount,
            checklist_reminders=checklist_reminders
        )

    def __dedup_search_list(self, items_by_target):
        clean_items_by_target = defaultdict(list)

        for target, items in items_by_target.items():
            merge_items = defaultdict(list)
            for item in items:
                if item['type'] == "pushplans":
                    clean_items_by_target[target].append(item)
                else:
                    merge_items[item['type']].append(item)

            for type_, items in merge_items.iteritems():
                if len(items) > 1:
                    users = set(item['user'] for item in items)
                    ids = [str(item['id']) for item in items]
                    is_complete = all([item['complete'] for item in items])
                    merged_item = {
                        "target": target,
                        "type": type_,
                        "complete": is_complete,
                        "id": u",".join(ids),
                        "request": 0, # this key is not used by template/js
                        "title": u"multiple requests",
                        "repo": u"multiple repositories",
                        "branch": u'multiple branches',
                        "user": u",".join(users)
                    }
                    clean_items_by_target[target].append(merged_item)
                elif len(items) == 1:
                    clean_items_by_target[target].append(items[0])

        return dict(clean_items_by_target)


class ChecklistToggleServlet(RequestHandler):

    def post(self):
        if not self.current_user:
            return self.send_error(403)

        self.checklist = core.util.get_int_arg(self.request, 'id')
        new_value = core.util.get_int_arg(self.request, 'complete')

        query = db.push_checklist.update().where(
            db.push_checklist.c.id == self.checklist).values({'complete': new_value})
        db.execute_cb(query, lambda _, __:self.finish())
