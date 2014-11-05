
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

    @mock.patch('pushmanager.ui_modules.urllib2.urlopen')
    def test_generate_test_tag_normal(self, mock_urlopen):
        m = mock.Mock()
        m.read.side_effect = ['{"tag" : "tag 0 fails"}', '{"url" : "results/sha"}']
        mock_urlopen.return_value = m

        MockedSettings['tests_tag'] = {}
        MockedSettings['tests_tag']['tag'] = 'test'
        MockedSettings['tests_tag']['tag_api_endpoint'] = 'example.com'
        MockedSettings['tests_tag']['tag_api_body'] = '{ "sha" : "%SHA%" }'
        MockedSettings['tests_tag']['url_api_endpoint'] = "http://example.com/api/v1/test_results_url"
        MockedSettings['tests_tag']['url_api_body'] = '{ "sha" : "%SHA%" }'
        MockedSettings['tests_tag']['servername'] = 'www.example.com'

        request_info = {'tags':'test', 'branch':'test', 'revision': 'abc123'}
        with mock.patch.dict(Settings, MockedSettings):
            request = Request(StubHandler())
            gen_tags = request._generate_tag_list(request_info, 'repo')
            T.assert_equals(gen_tags[0], ("tag 0 fails",  "www.example.com/results/sha"))

    @mock.patch('pushmanager.ui_modules.urllib2.urlopen')
    def test_generate_test_tag_no_url(self, mock_urlopen):
        m = mock.Mock()
        m.read.side_effect = ['{"tag" : "tag 0 fails"}', '{"url" : ""}']
        mock_urlopen.return_value = m

        MockedSettings['tests_tag'] = {}
        MockedSettings['tests_tag']['tag'] = 'test'
        MockedSettings['tests_tag']['tag_api_endpoint'] = 'example.com'
        MockedSettings['tests_tag']['tag_api_body'] = '{ "sha" : "%SHA%" }'
        MockedSettings['tests_tag']['url_api_endpoint'] = "http://example.com/api/v1/test_results_url"
        MockedSettings['tests_tag']['url_api_body'] = '{ "sha" : "%SHA%" }'
        MockedSettings['tests_tag']['servername'] = 'www.example.com'

        request_info = {'tags':'test', 'branch':'test', 'revision': 'abc123'}
        with mock.patch.dict(Settings, MockedSettings):
            request = Request(StubHandler())
            gen_tags = request._generate_tag_list(request_info, 'repo')
            T.assert_equals(gen_tags[0], ("tag 0 fails", None))

    def test_generate_test_tag_none(self):
        del MockedSettings['tests_tag']

        request_info = {'tags':'test', 'branch':'test', 'revision': 'abc123'}
        with mock.patch.dict(Settings, MockedSettings):
            request = Request(StubHandler())
            gen_tags = request._generate_tag_list(request_info, 'repo')
            T.assert_equals(gen_tags[0][0], "test")
