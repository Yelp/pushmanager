#!/usr/bin/env python

import copy
import datetime
import subprocess
import mock
import contextlib
import json

import testify as T
from pushmanager.core.util import add_to_tags_str
from pushmanager.core.util import del_from_tags_str
from pushmanager.core.util import dict_copy_keys
from pushmanager.core.util import EscapedDict
from pushmanager.core.util import get_servlet_urlspec
from pushmanager.core.util import pretty_date
from pushmanager.core.util import tags_contain
from pushmanager.core.util import tags_str_as_set
from pushmanager.core.util import send_people_msg_in_groups
from pushmanager.core.util import check_tag
from pushmanager.core.util import has_shipit
from pushmanager.core.util import does_review_sha_match_head_of_branch
from pushmanager.core.util import query_reviewboard
from pushmanager.servlets.pushes import PushesServlet


class CoreUtilFunctionsTest(T.TestCase):

    def test_pretty_date(self):
        now = datetime.datetime.now()
        five_minutes_ago = now - datetime.timedelta(minutes=5)
        seven_days_ago = now - datetime.timedelta(days=7)
        one_week_ago = now - datetime.timedelta(weeks=1)
        one_year_ago = now - datetime.timedelta(days=370)
        one_year_four_months_ago = now - datetime.timedelta(days=500)
        five_years_ago = now - datetime.timedelta(days=365 * 5)

        T.assert_equal(pretty_date(five_minutes_ago), "5 minutes ago")
        T.assert_equal(pretty_date(one_week_ago), "1 week ago")
        T.assert_equal(pretty_date(seven_days_ago), pretty_date(one_week_ago))
        T.assert_equal(pretty_date(one_year_ago), "1 year ago")
        T.assert_equal(pretty_date(one_year_four_months_ago), "1 year, 4 months ago")
        T.assert_equal(pretty_date(five_years_ago), "5 years ago")

    def test_servlet_urlspec(self):
        T.assert_equal(get_servlet_urlspec(PushesServlet), (r"/pushes", PushesServlet))

    def test_tags_str_as_set(self):
        T.assert_equal(set(), tags_str_as_set(""))
        T.assert_equal(set(), tags_str_as_set(","))
        T.assert_equal(set(["A"]), tags_str_as_set("A"))
        T.assert_equal(set(["A", "B"]), tags_str_as_set("A,B"))
        T.assert_equal(set(["A", "B", "C"]), tags_str_as_set("A,B,C"))
        T.assert_equal(set(["A", "B", "C"]), tags_str_as_set(" A  ,B  ,  C  "))

    def test_add_to_tags_str(self):
        T.assert_equal("A", add_to_tags_str("", "A"))
        T.assert_equal("A", add_to_tags_str("A", "A"))
        T.assert_equal("A,B", add_to_tags_str("A", "B"))
        T.assert_equal("A,B,C", add_to_tags_str("A,B", "C"))
        T.assert_equal("A,B,C", add_to_tags_str("A,B,C", "C"))
        T.assert_equal("A,B,C", add_to_tags_str("A", "A,B,C"))
        T.assert_equal("A,B", add_to_tags_str("A", "B"))
        T.assert_equal("A,B,C", add_to_tags_str("B,A", "C"))
        T.assert_equal("A,B,C", add_to_tags_str("A,C,B", "C"))
        T.assert_equal("A,B,C", add_to_tags_str("A", "B,A,C"))

    def test_del_from_tags_str(self):
        T.assert_equal("", del_from_tags_str("A", "A"))
        T.assert_equal("A", del_from_tags_str("A", "C"))
        T.assert_equal("A", del_from_tags_str("A", "B,C"))
        T.assert_equal("A,B", del_from_tags_str("A,B", "C"))
        T.assert_equal("A,B", del_from_tags_str("A,B,C", "C"))
        T.assert_equal("A,B", del_from_tags_str("A,C,B", "C"))
        T.assert_equal("B", del_from_tags_str("A,C,B", "C,A"))
        T.assert_equal("B,C", del_from_tags_str("A,C,B", "A,A,A"))
        T.assert_equal("B", del_from_tags_str("A, C  , B", " C ,A"))

    def test_tags_contains(self):
        T.assert_raises(TypeError, tags_contain, "A,B,C", None)
        T.assert_raises(AttributeError, tags_contain, None, [])
        T.assert_raises(AttributeError, tags_contain, None, None)
        T.assert_equal(tags_contain("", []), False)
        T.assert_equal(tags_contain("A,B,C", []), False)
        T.assert_equal(tags_contain("A,B,C", ["D"]), False)
        T.assert_equal(tags_contain("A", ["A"]), True)
        T.assert_equal(tags_contain("A,B,C", ["A"]), True)
        T.assert_equal(tags_contain("A,B,C", ["B"]), True)
        T.assert_equal(tags_contain("A,B,C", ["C"]), True)
        T.assert_equal(tags_contain("A,B,C", ["A", "C"]), True)
        T.assert_equal(tags_contain("A,B,C", ["A", "B"]), True)
        T.assert_equal(tags_contain("A,B,C", ["A", "B", "C"]), True)

    def test_dict_copy_keys(self):
        from_dict = {
            'a': 'lala',
            'b': 10,
            'c': {
                'x': 1,
                'y': 2,
            },
            (1, 2): 11,
        }
        to_dict = {
            (1, 2): None,
            'a': None,
            'c': {'x': None}
        }
        orig_to_dict = copy.deepcopy(to_dict)

        dict_copy_keys(to_dict, from_dict)

        T.assert_equal(sorted(to_dict.keys()), sorted(orig_to_dict))
        T.assert_equal(to_dict['a'], from_dict['a'])
        T.assert_equal(to_dict[(1, 2)], from_dict[(1, 2)])
        T.assert_equal(to_dict['c']['x'], from_dict['c']['x'])
        T.assert_equal(to_dict['c'].get('y', None), None)

    def test_send_people_msg_in_groups_split(self):
        people = ['111', '222', '333', '444', '555', '666']
        msg = 'Hello World!'
        irc_nick = 'Goku'
        irc_channel = 'dragon_ball'
        person_per_group = 5
        prefix_msg = '[fake_prefix_msg]'

        with contextlib.nested(
            mock.patch.object(subprocess, 'call', mock.Mock())
        ):
            send_people_msg_in_groups(people, msg, irc_nick, irc_channel, person_per_group, prefix_msg)

            T.assert_equal(subprocess.call.call_count, 2)
            subprocess.call.assert_any_call([
                '/nail/sys/bin/nodebot',
                '-i',
                'Goku',
                'dragon_ball',
                '[fake_prefix_msg] 111, 222, 333, 444, 555'
            ])

            subprocess.call.assert_any_call([
                '/nail/sys/bin/nodebot',
                '-i',
                'Goku',
                'dragon_ball',
                ' 666: Hello World!'
            ])

    def test_send_people_msg_in_groups_no_split(self):
        people = ['111', '222', '333', '444', '555', '666']
        msg = 'Hello World!'
        irc_nick = 'Goku'
        irc_channel = 'dragon_ball'
        person_per_group = 7
        prefix_msg = '[fake_prefix_msg]'

        with contextlib.nested(
            mock.patch.object(subprocess, 'call', mock.Mock())
        ):
            send_people_msg_in_groups(people, msg, irc_nick, irc_channel, person_per_group, prefix_msg)

            subprocess.call.assert_called_once_with([
                '/nail/sys/bin/nodebot',
                '-i',
                'Goku',
                'dragon_ball',
                '[fake_prefix_msg] 111, 222, 333, 444, 555, 666: Hello World!'
            ])

    def test_check_test_tag_has_seagull_tag(self):
        has_test_tag, msg = check_tag('seagull, tag', ['seagull'])
        T.assert_equal(has_test_tag, True)
        T.assert_equal(msg, '')

    def test_check_test_tag_has_both_tags(self):
        has_test_tag, msg = check_tag('seagull, buildbot', ['seagull'])
        T.assert_equal(has_test_tag, True)
        T.assert_equal(msg, '')

    def test_check_test_tag_has_no_tag(self):
        has_test_tag, msg = check_tag('no, tag', ['seagull'])
        T.assert_equal(has_test_tag, False)
        T.assert_equal(msg, 'Your request does not have following tag(s): seagull')

    def test_has_shipit(self):
        rb_stat = {
            'review_request': {
                'approved': True,
                'approval_failure': None
            }
        }
        has, msg = has_shipit(rb_stat)
        T.assert_equal(has, True)
        T.assert_equal(msg, '')

    def test_has_no_shipit(self):
        rb_stat = {
            'review_request': {
                'approved': False,
                'approval_failure': 'no shipit'
            }
        }
        has, msg = has_shipit(rb_stat)
        T.assert_equal(has, False)
        T.assert_equal(msg, 'no shipit')

    def test_reviewboard_failed_to_return_data(self):
        rb_stat = None
        has, msg = has_shipit(rb_stat)
        T.assert_equal(has, False)
        T.assert_equal(msg, 'Failed to verify shipit')

    def test_review_sha_matches_head_of_branch(self):
        rb_stat = {
            'review_request': {
                'commit_id': 'thisismysha'
            }
        }
        match, msg = does_review_sha_match_head_of_branch(rb_stat, 'thisismysha')
        T.assert_equal(match, True)
        T.assert_equal(msg, '')

    def test_review_sha_does_not_match_head_of_branch(self):
        rb_stat = {
            'review_request': {
                'commit_id': 'thisismysha'
            }
        }
        match, msg = does_review_sha_match_head_of_branch(rb_stat, 'thisismyheadsha')
        T.assert_equal(match, False)
        T.assert_equal(msg, 'Your sha of the review is not the same as HEAD of your branch')

    def test_reviewboard_failed_to_return_data_for_sha(self):
        rb_stat = None
        has_shipit, msg = does_review_sha_match_head_of_branch(rb_stat, 'mysha')
        T.assert_equal(has_shipit, False)
        T.assert_equal(msg, 'Failed to match review sha with head of branch')

    @mock.patch('pushmanager.core.util.tornado.httpclient.HTTPClient')
    def test_query_reviewboard_success(self, mockHTTPClient):
        client = mock.Mock()
        mockHTTPClient.return_value = client
        mock_response = mock.Mock()
        mock_response.body = '{"review_request": {"approved":"True", "approval_failure": null}}'
        client.fetch = mock.Mock(return_value=mock_response)
        rb_stat = query_reviewboard(1, 'my_reviewboard_server', 'my_user', 'my_pass')
        client.fetch.assert_called_once_with(
            'http://my_reviewboard_server/api/review-requests/1/',
            auth_username='my_user',
            auth_password='my_pass'
        )
        T.assert_equal(rb_stat, json.loads('{"review_request": {"approved":"True", "approval_failure": null}}'))

    @mock.patch('pushmanager.core.util.tornado.httpclient.HTTPClient')
    def test_check_reviewboard_failure(self, mockHTTPClient):
        client = mock.Mock()
        mockHTTPClient.return_value = client
        client.fetch = mock.Mock(side_effect=Exception('bad request'))

        rb_stat = query_reviewboard(1, 'my_reviewboard_server', 'my_user', 'my_pass')
        T.assert_equal(rb_stat, None)


class CoreUtilEscapedDictTest(T.TestCase):

    @T.class_setup
    def setup_dictionary(self):
        self.d = {
            "amp": "Music & Fun!",
            "gt": "A is greater than B ( A > B )"
            }

        self.ed = EscapedDict(self.d)

        self.escaped = {
            "amp": "Music &amp; Fun!",
            "gt": "A is greater than B ( A &gt; B )"
            }

    def test_escape(self):
        T.assert_equal(
            [k for k in self.d if self.ed[k] != self.escaped[k]],
            [],
            "EscapedDict values doesn't match with pre-computed valued"
        )
        T.assert_in("&amp;", self.ed['amp'])
        T.assert_not_in(">", self.ed['gt'])
