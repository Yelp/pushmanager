# -*- coding: utf-8 -*-
"""
Renames a tag for all push requests in the database.

With an appropriate config.yaml running from the root of the pushmanager-service:
python -u tools/rename_tag.py oldtag newtag

Reverting the change (if tags are unique) is as simple as swapping the tags.

Note:

Some tag renames may need to be accompanied with a checklist_type rename as
well. Tags handled specially in the pushmanager will also need corresponding
code changes.
"""
import sys
from functools import partial
from optparse import OptionParser

import pushmanager.core.db as db
from pushmanager.core.util import add_to_tags_str
from pushmanager.core.util import del_from_tags_str
from pushmanager.core.util import tags_contain
from pushmanager.servlets.checklist import checklist_reminders


def main():
    usage = 'usage: %prog <oldtype> <newtype>'
    parser = OptionParser(usage)
    (_, args) = parser.parse_args()

    if len(args) == 2:
        db.init_db()
        convert_tag(args[0], args[1])
        db.finalize_db()
    else:
        parser.error('Incorrect number of arguments')


def convert_tag(old, new):
    print 'Renaming %s to %s in tags' % (old, new)

    cb = partial(convert_tag_callback, old, new)

    rselect_query = db.push_requests.select()
    db.execute_transaction_cb([rselect_query], cb)

    if old in checklist_reminders.keys():
        print """%s is handled specially in pushmanager.
Additional code changes are required before pushmanger can be restarted.
""" % old


def convert_tag_callback(oldtag, newtag, success, db_results):
    check_db_results(success, db_results)

    requests = db_results[0].fetchall()

    update_queries = []
    for request in requests:
        if tags_contain(request['tags'], [oldtag]):
            updated_tags = del_from_tags_str(request['tags'], oldtag)
            updated_tags = add_to_tags_str(updated_tags, newtag)
            update_query = db.push_requests.update().where(
                db.push_requests.c.id == request.id
                ).values({'tags': updated_tags})
            update_queries.append(update_query)

    db.execute_transaction_cb(update_queries, check_db_results)


def check_db_results(success, db_results):
    if not success:
        raise db.DatabaseError()


if __name__ == '__main__':
    sys.exit(main())
