import testify as T
from pushmanager.ui_methods import authorized_to_manage_request


class UIMethodTest(T.TestCase):

    def test_authorized_to_manage_request_random_user(self):
        request = {'user': 'testuser', 'watchers': None }
        T.assert_equal(False, authorized_to_manage_request(None, request, 'notme'))

    def test_authorized_to_manage_request_request_user(self):
        request = {'user': 'testuser', 'watchers': None }
        T.assert_equal(True, authorized_to_manage_request(None, request, 'testuser'))

    def test_authorized_to_manage_request_pushmaster(self):
        request = {'user': 'testuser', 'watchers': None }
        T.assert_equal(True, authorized_to_manage_request(None, request, 'notme', True))

    def test_authorized_to_manage_request_watcher(self):
        request = {'user': 'testuser', 'watchers': 'watcher1' }
        T.assert_equal(True, authorized_to_manage_request(None, request, 'watcher1'))


if __name__ == '__main__':
    T.run()
