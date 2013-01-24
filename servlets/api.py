import json
import sqlalchemy as SA

from core import db
from core import util
from core.requesthandler import RequestHandler

class APIServlet(RequestHandler):

    # Regexp part of the URLSpec, to be used in
    # tornado.web.Application initialization with APIServlet handler.
    regexp = r'/api(?:/([^/]+))?'

    def get(self, endpoint):
        if endpoint:
            func = '_api_%s' % endpoint.upper()
            if hasattr(self, func):
                return getattr(self, func)()
        return self.redirect("https://github.com/Yelp/pushmanager/wiki/Pushmanager-API")

    post = get

    def _xjson(self, data):
        self.set_header("Content-Type", "application/json")
        self.write(json.dumps(data))
        return self.finish()

    def _api_USERLIST(self):
        """Returns a JSON list of users who used PushManager for a request at least once."""
        query = db.push_requests.select(
            group_by=db.push_requests.c.user,
        )
        db.execute_cb(query, self._on_USERLIST_db_response)

    def _on_USERLIST_db_response(self, success, db_results):
        self.check_db_results(success, db_results)
        return self._xjson([r['user'] for r in db_results])

    def _api_REQUEST(self):
        """Returns a JSON representation of a push request."""
        request_id = util.get_int_arg(self.request, 'id')
        if not request_id:
            return self.send_error(404)

        query = db.push_requests.select(db.push_requests.c.id == request_id)
        db.execute_cb(query, self._on_REQUEST_db_response)

    def _on_REQUEST_db_response(self, success, db_results):
        self.check_db_results(success, db_results)

        request = db_results.first()
        if not request:
            return self.send_error(404)
        else:
            return self._xjson(util.request_to_jsonable(request))

    def _api_PUSH(self):
        """Returns a JSON representation of a push."""
        push_id = util.get_int_arg(self.request, 'id')
        if not push_id:
            return self.send_error(404)

        query = db.push_pushes.select(db.push_pushes.c.id == push_id)
        db.execute_cb(query, self._on_PUSH_db_response)

    def _on_PUSH_db_response(self, success, db_results):
        if not success:
            return self.send_error(500)

        push = db_results.first()
        if not push:
            return self.send_error(404)
        else:
            return self._xjson(util.push_to_jsonable(push))

    def _api_PUSHDATA(self):
        """Returns all the information on a push in JSON. This is the same data that is shown on the push page"""
        push_id = util.get_int_arg(self.request, 'id')
        if not push_id:
            return self.send_error(404)

        push_info_query = db.push_pushes.select(db.push_pushes.c.id == push_id)
        contents_query = db.push_requests.select(
            SA.and_(
                db.push_requests.c.id == db.push_pushcontents.c.request,
                db.push_pushcontents.c.push == push_id,
            ),
            order_by=(db.push_requests.c.user, db.push_requests.c.title),
        )
        available_query = db.push_requests.select(
            db.push_requests.c.state == 'requested',
        )
        db.execute_transaction_cb([push_info_query, contents_query, available_query], self._on_PUSHDATA_db_response)

    def _on_PUSHDATA_db_response(self, success, db_results):
        self.check_db_results(success, db_results)

        push_info, push_contents, available_requests = db_results
        push_info = push_info.first()
        if not push_info:
            return self.send_error(404)
        push_info = util.push_to_jsonable(push_info)

        available_requests = [util.request_to_jsonable(r) for r in available_requests.fetchall()]
        push_requests = {}
        for request in push_contents:
            request = util.request_to_jsonable(request)
            push_requests.setdefault(request['state'], []).append(request)
            push_requests.setdefault('all', []).append(request)

        return self._xjson([push_info, push_requests, available_requests])

    def _api_PUSHES(self):
        """Returns a JSON representation of pushes."""
        rpp = int(self.request.arguments.get('rpp', [50])[0])
        before = int(self.request.arguments.get('before', [0])[0])
        if before > 0:
            push_query = db.push_pushes.select(
                    whereclause=(db.push_pushes.c.id < before),
                    order_by=db.push_pushes.c.modified.desc(),
                )
        else:
            push_query = db.push_pushes.select(
                    order_by=db.push_pushes.c.modified.desc(),
                )

        if rpp > 0:
            push_query = push_query.limit(rpp)

        last_push_query = SA.select(
            columns=[SA.func.max(db.push_pushes.c.id)]
        )

        db.execute_transaction_cb([push_query, last_push_query,], self._on_PUSHES_db_response)

    def _on_PUSHES_db_response(self, success, db_results):
        self.check_db_results(success, db_results)

        push_results, last_push_results = db_results
        push_results = [util.push_to_jsonable(result) for result in push_results]
        return self._xjson([push_results, last_push_results.first()[0]])

    def _api_PUSHCONTENTS(self):
        """Returns a set of JSON representations of requests in a given push."""
        push_id = util.get_int_arg(self.request, 'id')
        if not push_id:
            return self.send_error(404)

        query = db.push_requests.select(SA.and_(
                db.push_requests.c.id == db.push_pushcontents.c.request,
                db.push_pushcontents.c.push == push_id,
            ))
        db.execute_cb(query, self._on_PUSHCONTENTS_db_response)

    def _on_PUSHCONTENTS_db_response(self, success, db_results):
        self.check_db_results(success, db_results)

        requests = [util.request_to_jsonable(request) for request in db_results]
        return self._xjson(requests)

    def _api_PUSHBYREQUEST(self):
        """Returns a JSON representation of a PUSH given a request id."""
        request_id = util.get_int_arg(self.request, 'id')
        if not request_id:
            return self.send_error(404)

        query = db.push_pushes.select(SA.and_(
            db.push_pushes.c.state != "discarded",
            db.push_pushcontents.c.push == db.push_pushes.c.id,
            db.push_pushcontents.c.request == request_id,
        ))
        db.execute_cb(query, self._on_PUSHBYREQUEST_db_response)

    def _on_PUSHBYREQUEST_db_response(self, success, db_results):
        self.check_db_results(success, db_results)

        push = db_results.first()
        return self._xjson(util.push_to_jsonable(push))

    def _api_PUSHITEMS(self):
        """Returns a JSON representation of a list of requests given a push id"""
        push_id = util.get_int_arg(self.request, 'push_id')
        if not push_id:
            return self.send_error(404)

        query = db.push_requests.select(
            SA.and_(
                db.push_requests.c.id == db.push_pushcontents.c.request,
                db.push_requests.c.state != 'pickme',
                db.push_pushcontents.c.push == push_id,
                ),
            order_by=(db.push_requests.c.user, db.push_requests.c.title),
        )
        db.execute_cb(query, self._on_PUSHITEMS_db_response)

    def _on_PUSHITEMS_db_response(self, success, db_results):
        self.check_db_results(success, db_results)
        return self._xjson([util.request_to_jsonable(request) for request in db_results])

    def _api_REQUESTSEARCH(self):
        """Returns a list of requests matching a the specified filter(s)."""
        filters = []

        # Tag constraint
        for tag in self.request.arguments.get('tag', []):
            filters.append(db.push_requests.c.tags.op('regexp')('[[:<:]]' + tag + '[[:>:]]'))

        # Timestamp constraint
        mbefore = util.get_int_arg(self.request, 'mbefore')
        mafter = util.get_int_arg(self.request, 'mafter')
        if mbefore:
            filters.append(db.push_requests.c.modified < mbefore)
        if mafter:
            filters.append(db.push_requests.c.modified > mafter)

        cbefore = util.get_int_arg(self.request, 'cbefore')
        cafter = util.get_int_arg(self.request, 'cafter')
        if cbefore:
            filters.append(db.push_requests.c.created < cbefore)
        if cafter:
            filters.append(db.push_requests.c.created > cafter)

        # State constraint
        states = self.request.arguments.get('state', [])
        if states:
            filters.append(db.push_requests.c.state.in_(states))

        # User constraint
        users = self.request.arguments.get('user', [])
        if users:
            filters.append(db.push_requests.c.user.in_(users))

        # Repository constraint
        repos = self.request.arguments.get('repo', [])
        if repos:
            filters.append(db.push_requests.c.repo.in_(repos))

        # Branch constraint
        branches = self.request.arguments.get('branch', [])
        if branches:
            filters.append(db.push_requests.c.branch.in_(branches))

        # Revision constraint
        revisions = self.request.arguments.get('rev', [])
        if revisions:
            filters.append(db.push_requests.c.revision.in_(revisions))

        # Review constraint
        reviews = self.request.arguments.get('review', [])
        if reviews:
            filters.append(db.push_requests.c.reviewid.in_(reviews))

        # Title constraint
        for title in self.request.arguments.get('title', []):
            filters.append(db.push_requests.c.title.like('%' + title + '%'))

        # Only allow searches with at least one constraint (to avoid
        # accidental dumps of the entire table)
        if not filters:
            return self.send_error(409)

        query = db.push_requests.select(SA.and_(*filters))
        query = query.order_by(db.push_requests.c.id.desc())

        limit = util.get_int_arg(self.request, 'limit')
        if limit > 0:
            limit = max(min(1000, limit), 1)
            query = query.limit(limit)

        db.execute_cb(query, self._on_REQUESTSEARCH_db_response)

    def _on_REQUESTSEARCH_db_response(self, success, db_results):
        if not success:
            return self.send_error(500)

        requests = [util.request_to_jsonable(request) for request in db_results]
        return self._xjson(requests)
