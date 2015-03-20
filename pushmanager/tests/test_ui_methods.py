import testify as T
from pushmanager.ui_methods import authorized_to_manage_request
from pushmanager.ui_methods import sort_pickmes


class UIMethodTest(T.TestCase):

    def test_authorized_to_manage_request_random_user(self):
        request = {'user': 'testuser', 'watchers': None}
        T.assert_equal(False, authorized_to_manage_request(None, request, 'notme'))

    def test_authorized_to_manage_request_request_user(self):
        request = {'user': 'testuser', 'watchers': None}
        T.assert_equal(True, authorized_to_manage_request(None, request, 'testuser'))

    def test_authorized_to_manage_request_pushmaster(self):
        request = {'user': 'testuser', 'watchers': None}
        T.assert_equal(True, authorized_to_manage_request(None, request, 'notme', True))

    def test_authorized_to_manage_request_watcher(self):
        request = {'user': 'testuser', 'watchers': 'watcher1'}
        T.assert_equal(True, authorized_to_manage_request(None, request, 'watcher1'))

    def test_sort_pickmes_regular_case(self):
        requests = [
            {'tags': 'fake_tags', 'user': 'userA'},
            {'tags': 'fake_tags', 'user': 'userB'},
            {'tags': 'urgent,no-verify', 'user': 'userA'},
            {'tags': 'urgent,no-verify', 'user': 'userA'},
            {'tags': 'urgent,no-verify', 'user': 'userB'},
            {'tags': 'urgent,no-verify', 'user': 'userB'},
            {'tags': 'urgent', 'user': 'userA'},
            {'tags': 'urgent,no-verify,seagull', 'user': 'userB'},
        ]

        sorted_requests = sort_pickmes(None, requests, ['urgent', 'no-verify', 'seagull'])

        T.assert_equal(len(sorted_requests), 8)
        T.assert_equal(sorted_requests[0], {'tags': 'urgent,no-verify,seagull', 'user': 'userB'})
        T.assert_equal(sorted_requests[1], {'tags': 'urgent,no-verify', 'user': 'userA'})
        T.assert_equal(sorted_requests[2], {'tags': 'urgent,no-verify', 'user': 'userA'})
        T.assert_equal(sorted_requests[3], {'tags': 'urgent,no-verify', 'user': 'userB'})
        T.assert_equal(sorted_requests[4], {'tags': 'urgent,no-verify', 'user': 'userB'})
        T.assert_equal(sorted_requests[5], {'tags': 'urgent', 'user': 'userA'})
        T.assert_equal(sorted_requests[6], {'tags': 'fake_tags', 'user': 'userA'})
        T.assert_equal(sorted_requests[7], {'tags': 'fake_tags', 'user': 'userB'})

    def test_sort_pickmes_all_tags_in_ordering(self):
        requests = [
            {'tags': 'no-verify', 'user': 'userA'},
            {'tags': 'urgent', 'user': 'userC'},
            {'tags': 'seagull', 'user': 'userA'},
            {'tags': 'no-verify', 'user': 'userA'},
            {'tags': 'seagull', 'user': 'userB'},
            {'tags': 'seagull', 'user': 'userB'},
            {'tags': 'no-verify', 'user': 'userA'},
            {'tags': 'seagull', 'user': 'userB'},
            {'tags': 'no-verify', 'user': 'userB'},
        ]

        sorted_requests = sort_pickmes(None, requests, ['urgent', 'no-verify', 'seagull'])

        T.assert_equal(len(sorted_requests), 9)
        T.assert_equal(sorted_requests[0], {'tags': 'urgent', 'user': 'userC'})
        T.assert_equal(sorted_requests[1], {'tags': 'no-verify', 'user': 'userA'})
        T.assert_equal(sorted_requests[2], {'tags': 'no-verify', 'user': 'userA'})
        T.assert_equal(sorted_requests[3], {'tags': 'no-verify', 'user': 'userA'})
        T.assert_equal(sorted_requests[4], {'tags': 'no-verify', 'user': 'userB'})
        T.assert_equal(sorted_requests[5], {'tags': 'seagull', 'user': 'userA'})
        T.assert_equal(sorted_requests[6], {'tags': 'seagull', 'user': 'userB'})
        T.assert_equal(sorted_requests[7], {'tags': 'seagull', 'user': 'userB'})
        T.assert_equal(sorted_requests[8], {'tags': 'seagull', 'user': 'userB'})

    def test_sort_pickmes_no_tags_order(self):
        requests = [
            {'tags': 'no-verify', 'user': 'userA'},
            {'tags': 'urgent', 'user': 'userB'},
            {'tags': 'seagull', 'user': 'userC'},
        ]

        sorted_requests = sort_pickmes(None, requests, [])

        T.assert_equal(len(sorted_requests), 3)
        T.assert_equal(sorted_requests[0], {'tags': 'no-verify', 'user': 'userA'})
        T.assert_equal(sorted_requests[1], {'tags': 'urgent', 'user': 'userB'})
        T.assert_equal(sorted_requests[2], {'tags': 'seagull', 'user': 'userC'})


if __name__ == '__main__':
    T.run()
