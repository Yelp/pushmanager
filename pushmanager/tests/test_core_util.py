#!/usr/bin/env python

import copy
import datetime
import subprocess
import mock
import contextlib

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
                '[fake_prefix_msg]111, 222, 333, 444, 555'
            ])

            subprocess.call.assert_any_call([
                '/nail/sys/bin/nodebot',
                '-i',
                'Goku',
                'dragon_ball',
                '666: Hello World!'
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
                '[fake_prefix_msg]111, 222, 333, 444, 555, 666: Hello World!'
            ])


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
