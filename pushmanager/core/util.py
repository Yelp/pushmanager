import copy
import datetime
import subprocess
import logging
import json

from tornado.escape import xhtml_escape
import tornado.httpclient


class EscapedDict(object):
    """
    A wrapper for a dict that (by default) HTML-escapes values as you ask for
    them. If a value should not be escaped because it is going to be used as
    HTML, it can be specified as such using unescape_key.
    """
    def __init__(self, doc):
        self.doc = doc
        self.no_escape = {}

    def unescape_key(self, key):
        self.no_escape[key] = True

    def escape_key(self, key):
        self.no_escape[key] = False

    def __getitem__(self, key):
        escape = True
        if key in self.no_escape and self.no_escape[key] == True:
            escape = False

        item = self.doc[key]
        if isinstance(item, str) and escape:
            return xhtml_escape(self.doc[key])
        else:
            return self.doc[key]


def get_int_arg(request, field, default=None):
    """Try to get an integer value from a query arg."""
    try:
        val = int(request.arguments.get(field, [default])[0])
    except (ValueError, TypeError):
        val = default
    return val


def get_str_arg(request, field, default=None):
    """Try to get a string value from a query arg."""
    return request.arguments.get(field, [default])[0]


def sqlalchemy_to_dict(result, table):
    row_item = {}
    for col in table.columns.keys():
        row_item[col] = getattr(result, col)
    return row_item


def pretty_date(time=False):
    """
    Get a datetime object or a int() Epoch timestamp and return a
    pretty string like 'an hour ago', 'Yesterday', '3 months ago',
    'just now', etc
    """
    now = datetime.datetime.now()
    if type(time) is int:
        diff = now - datetime.datetime.fromtimestamp(time)
    elif isinstance(time, datetime.datetime):
        diff = now - time
    elif not time:
        diff = now - now
    else:
        raise ValueError('need to provide either int, datetime, or None for "time" arg')
    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return ''

    if day_diff == 0:
        if second_diff < 10:
            return "just now"
        if second_diff < 60:
            return str(second_diff) + " seconds ago"
        if second_diff < 120:
            return "a minute ago"
        if second_diff < 3600:
            return str(second_diff / 60) + " minutes ago"
        if second_diff < 7200:
            return "an hour ago"
        if second_diff < 86400:
            return str(second_diff / 3600) + " hours ago"
    if day_diff == 1:
        return "yesterday"
    if day_diff < 7:
        return str(day_diff) + " days ago"
    if day_diff < 14:
        return "1 week ago"
    if day_diff < 31:
        return str(day_diff/7) + " weeks ago"
    if day_diff < 60:
        return "1 month ago"
    if day_diff < 365:
        return str(day_diff/30) + " months ago"
    if day_diff < 365 * 2:
        remainder = datetime.datetime.now() - (diff - datetime.timedelta(days=365))
        diff = now - remainder
        if diff.days > 31:
            return "1 year, " + pretty_date(remainder)
        else:
            return "1 year ago"
    return str(day_diff/365) + " years ago"


def get_servlet_urlspec(servlet):
    try:
        return (servlet.regexp, servlet)
    except AttributeError:
        name = servlet.__name__
        regexp = r"/%s" % name[:-len("Servlet")].lower()
        return (regexp, servlet)


def tags_str_as_set(tags_str):
    """Return comma separated tags list string as a set, stripping out
    surrounding white space if necessary.
    """
    return set(filter(lambda t: t != '', (t.strip() for t in tags_str.split(','))))


def tags_contain(tags_str, contains_list):
    """Predicate to check if a tags string list contains any of the
    tags in contains_list.

    Args:
    tags_str - comma-separated string of request tags.
    contains_list - list of request tag strings.
    """
    return len(tags_str_as_set(tags_str) & set(contains_list)) > 0


def add_to_tags_str(current_tags, tags):
    """Args:
    current_tags - A comma-separated string comprising a list of tags
    from the current request.
    tags - A comma-separated string comprising a list of tags which
    should be added to current_tags.

    Returns: a comma-separated string which is the union of the sets
    represented by current_tags and tags, sorted alphabetically.
    """
    return ','.join(
        sorted(tags_str_as_set(current_tags) | tags_str_as_set(tags))
    )


def del_from_tags_str(current_tags, tags):
    """Args:
    current_tags - A comma-separated string comprising a list of tags
    from the current request.
    tags - A comma-separated string comprising a list of tags which
    should be removed from current_tags.

    Returns: a comma-separted string which is the difference of
    current_tags from tags, sorted alphabetically.
    """
    return ','.join(
        sorted(tags_str_as_set(current_tags).difference(tags_str_as_set(tags)))
    )


def request_to_jsonable(request):
    """Get a request object and return a dict with desired key, value
    pairs that are to be encoded to json format
    """
    return dict(
        (k, request[k]) for k in (
            'id',
            'user',
            'watchers',
            'state',
            'repo',
            'branch',
            'revision',
            'tags',
            'conflicts',
            'created',
            'modified',
            'title',
            'comments',
            'reviewid',
            'description'
        )
    )


def push_to_jsonable(push):
    """Get a push object and return a dict with desired key, value
    pairs that are to be encoded to json format
    """
    return dict(
        (k, push[k]) for k in (
            'id',
            'title',
            'user',
            'branch',
            'stageenv',
            'state',
            'created',
            'modified',
            'pushtype',
            'extra_pings'
        )
    )


def dict_copy_keys(to_dict, from_dict):
    """Copy the values from from_dict to to_dict but only the keys
    that are present in to_dict
    """
    for key, value in to_dict.items():
        if key not in from_dict:
            del to_dict[key]
        elif type(value) is dict:
            dict_copy_keys(value, from_dict[key])
        else:
            to_dict[key] = copy.deepcopy(from_dict[key])


def send_people_msg_in_groups(people, msg, irc_nick, irc_channel, person_per_group=-1, prefix_msg=''):
    """Send multiple people message.
    """
    people = list(people)  # people argument is a set
    if person_per_group <= 0:
        groups = [people[:]]  # do not split
    else:
        groups = [people[i:i+person_per_group] for i in range(0, len(people), person_per_group)]

    for i, group in enumerate(groups):
        irc_message = u'{0} {1}{2}'.format(
            prefix_msg if (not i and len(prefix_msg) != 0) else '',
            ', '.join(group),
            ': ' + msg if i == len(groups) - 1 else '',
        )

        subprocess.call([
            '/nail/sys/bin/nodebot',
            '-i',
            irc_nick,
            irc_channel,
            irc_message
        ])


def query_reviewboard(reviewid, servername, username, password):
    """Get review data for a reviewID.

    Args:
    reviewid   - review id
    servername - reviewboard hostname
    username   - reviewboard username
    password   - reviewboard password

    Returns: review data
    """
    rb_stat = None
    http_client = tornado.httpclient.HTTPClient()
    try:
        response = http_client.fetch("http://%s/api/review-requests/%d/" % (
                servername,
                reviewid
            ),
            auth_username=username,
            auth_password=password
        )
        rb_stat = json.loads(response.body)
    except Exception:
        logging.error("Failed to query reviewboard for review %d" % reviewid)
    http_client.close()
    return rb_stat


def does_review_sha_match_head_of_branch(rb_stat, head_sha):
    """check whether review sha matches head of branch.

    Args:
    rb_stat  - dict returned by reviewboard api
    head_sha - head of branch

    Returns: (status, error_msg)
    """
    if rb_stat is None:
        return (False, 'Failed to match review sha with head of branch')

    match = rb_stat['review_request']['commit_id'] == head_sha
    msg = '' if match else 'Your sha of the review is not the same as HEAD of your branch'
    return (match, msg)


def has_shipit(rb_stat):
    """Check whether review has a shipit from primary reviewer.

    Args:
    rb_stat - dict returned by reviewboard api

    Returns: (status, error_msg)
    """
    if rb_stat is None:
        return (False, 'Failed to verify shipit')

    has_shipit = rb_stat['review_request']['approved']
    msg = '' if has_shipit else rb_stat['review_request']['approval_failure']
    return (has_shipit, msg)


def check_tag(tags, tags_to_check):
    """Check whether requests contain certain tags.

    Args:
    tags          - tags from requests
    tags_to_check - tags we need to validate

    Return: (status, error_message)
    """
    has_test_tag = tags_contain(tags, tags_to_check)
    msg = 'Your request does not have following tag(s): %s' % ','.join(tags_to_check)
    return (has_test_tag, '' if has_test_tag else msg)
