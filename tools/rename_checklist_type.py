# -*- coding: utf-8 -*-
"""
Renames a checklist type for all checklists in the database.

 A checklist type may have two forms - name and name-cleanup.

With an appropriate config.yaml running from the root of the pushmanager-service:
python -u tools/rename_checklist_type.py oldname newname

Reverting the change (if tags are unique) is as simple as swapping the tags.

Note:

Checklist type renames will mostly require code changes.
"""
import sys
from functools import partial
from optparse import OptionParser

import pushmanager.core.db as db


def main():
    usage = 'usage: %prog <oldtag> <newtag>'
    parser = OptionParser(usage)
    (_, args) = parser.parse_args()

    if len(args) == 2:
        db.init_db()
        convert_checklist(args[0], args[1])
        db.finalize_db()
    else:
        parser.error('Incorrect number of arguments')

def convert_checklist(old, new):
    print 'Renaming %s to %s in checklist types' % (old, new)

    cb = partial(convert_checklist_callback, old, new)

    cselect_query = db.push_checklist.select()
    db.execute_transaction_cb([cselect_query], cb)


def convert_checklist_callback(old, new, success, db_results):
    check_db_results(success, db_results)

    checklists = db_results[0].fetchall()

    convert = {
        old: new,
        '%s-cleanup' % old: '%s-cleanup' % new
    }

    update_queries = []
    for checklist in checklists:
        if checklist['type'] in convert.keys():
            update_query = db.push_checklist.update().where(
                db.push_checklist.c.id == checklist.id
                ).values({'type': convert[checklist['type']]})
            update_queries.append(update_query)

    db.execute_transaction_cb(update_queries, check_db_results)

def check_db_results(success, db_results):
    if not success:
        raise db.DatabaseError()


if __name__ == '__main__':
    sys.exit(main())
