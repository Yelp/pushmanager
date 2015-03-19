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
            {'tags': 'fake_tags'},
            {'tags': 'urgent,no-verify'},
            {'tags': 'urgent'},
            {'tags': 'urgent,no-verify,seagull'},
        ]

        sorted_requests = sort_pickmes(None, requests, ['urgent', 'no-verify', 'seagull'])
        T.assert_equal(len(sorted_requests), 4)
        T.assert_equal(sorted_requests[0], {'tags': 'urgent,no-verify,seagull'})
        T.assert_equal(sorted_requests[1], {'tags': 'urgent,no-verify'})
        T.assert_equal(sorted_requests[2], {'tags': 'urgent'})
        T.assert_equal(sorted_requests[3], {'tags': 'fake_tags'})

    def test_sort_pickmes_all_tags_in_ordering(self):
        requests = [
            {'tags': 'no-verify'},
            {'tags': 'urgent'},
            {'tags': 'seagull'},
        ]

        sorted_requests = sort_pickmes(None, requests, ['urgent', 'no-verify', 'seagull'])
        T.assert_equal(len(sorted_requests), 3)
        T.assert_equal(sorted_requests[0], {'tags': 'urgent'})
        T.assert_equal(sorted_requests[1], {'tags': 'no-verify'})
        T.assert_equal(sorted_requests[2], {'tags': 'seagull'})

    def test_sort_pickmes_no_tags_order(self):
        requests = [
            {'tags': 'no-verify'},
            {'tags': 'urgent'},
            {'tags': 'seagull'},
        ]

        sorted_requests = sort_pickmes(None, requests, [])
        T.assert_equal(len(sorted_requests), 3)
        T.assert_equal(sorted_requests[0], {'tags': 'no-verify'})
        T.assert_equal(sorted_requests[1], {'tags': 'urgent'})
        T.assert_equal(sorted_requests[2], {'tags': 'seagull'})


if __name__ == '__main__':
    T.run()
