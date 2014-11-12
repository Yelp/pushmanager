import mock
import testify as T
from pushmanager.ui_modules import Request
from pushmanager.core.settings import Settings
from pushmanager.testing.mocksettings import MockedSettings

class StubHandler(object):
    def __init__(self):
        self.request = 'request'
        self.ui = 'ui'
        self.current_user = 'curr_user'
        self.locale = 'the_moon'

class UIModuleTest(T.TestCase):

    def test_generate_tag_list_no_special(self):
        request = Request(StubHandler())
        request_info = {'tags':'git-not-ok', 'branch':'test'}
        MockedSettings['git']['gitweb_servername'] = 'example.com'
        with mock.patch.dict(Settings, MockedSettings):
            gen_tags = request._generate_tag_list(request_info, 'repo')
            T.assert_equals(gen_tags[0][1], None)

    def test_generate_tag_list_gitok(self):
        request = Request(StubHandler())
        request_info = {'tags':'git-ok', 'branch':'test'}
        MockedSettings['git']['gitweb_servername'] = 'example.com'
        with mock.patch.dict(Settings, MockedSettings):
            gen_tags = request._generate_tag_list(request_info, 'repo')
            T.assert_equals(gen_tags[0][1], 'https://example.com/?p=repo.git;a=log;h=refs/heads/test')
