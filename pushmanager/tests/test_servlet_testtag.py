import mock
import testify as T

from pushmanager.testing.mocksettings import MockedSettings
from pushmanager.servlets.testtag import TestTagServlet
from pushmanager.core.settings import Settings


class TestTagServletTest(T.TestCase):

    @mock.patch('pushmanager.servlets.testtag.urllib2.urlopen')
    def test_generate_test_tag_normal(self, mock_urlopen):
        m = mock.Mock()
        m.read.side_effect = ['{"tag" : "tag 0 fails"}', '{"id" : "123"}']
        mock_urlopen.return_value = m

        MockedSettings['tests_tag'] = {}
        MockedSettings['tests_tag']['tag'] = 'test'
        MockedSettings['tests_tag']['tag_api_endpoint'] = 'example.com'
        MockedSettings['tests_tag']['tag_api_body'] = '{ "sha" : "%SHA%" }'
        MockedSettings['tests_tag']['url_api_endpoint'] = "http://example.com/api/v1/test_results_url"
        MockedSettings['tests_tag']['url_api_body'] = '{ "sha" : "%SHA%" }'
        MockedSettings['tests_tag']['servername'] = 'www.example.com/%ID%'

        request_info = {'tags':'test', 'branch':'test', 'revision': 'abc123'}
        with mock.patch.dict(Settings, MockedSettings):
            gen_tags = TestTagServlet._gen_test_tag_resp(request_info)
            T.assert_equals({'tag': 'tag 0 fails', 'url': "www.example.com/123"}, gen_tags)

    @mock.patch('pushmanager.servlets.testtag.urllib2.urlopen')
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
        MockedSettings['tests_tag']['servername'] = 'www.example.com/%ID$'

        request_info = {'tags':'test', 'branch':'test', 'revision': 'abc123'}
        with mock.patch.dict(Settings, MockedSettings):
            gen_tags = TestTagServlet._gen_test_tag_resp(request_info)
            T.assert_equals({'tag': 'tag 0 fails', 'url': ""}, gen_tags)

    def test_generate_test_tag_none(self):
        del MockedSettings['tests_tag']

        request_info = {'tags':'test', 'branch':'test', 'revision': 'abc123'}
        with mock.patch.dict(Settings, MockedSettings):
            gen_tags = TestTagServlet._gen_test_tag_resp(request_info)
            T.assert_equals({}, gen_tags)
