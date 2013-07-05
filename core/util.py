import copy
import datetime

from tornado.escape import xhtml_escape

class EscapedDict:
    """A wrapper for a dict that HTML-escapes values as you ask for them"""
    def __init__(self, doc):
        self.doc = doc
    def __getitem__(self, key):
        item = self.doc[key]
        if isinstance(item, str):
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
    elif isinstance(time,datetime.datetime):
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
            return  "a minute ago"
        if second_diff < 3600:
            return str( second_diff / 60 ) + " minutes ago"
        if second_diff < 7200:
            return "an hour ago"
        if second_diff < 86400:
            return str( second_diff / 3600 ) + " hours ago"
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
        if type(value) is dict:
            dict_copy_keys(value, from_dict[key])
        else:
            to_dict[key] = copy.deepcopy(from_dict[key])
