import testing as T

class RequestTemplateTest(T.TemplateTestCase):

    authenticated = True
    request_page = 'modules/request.html'
    request_info_page = 'modules/request-info.html'

    basic_request = {
            'id': 0,
            'repo': 'non-existent',
            'branch': 'non-existent',
            'reviewid': 0,
            'title': 'some title',
            'revision': '0' * 40,
            'state': 'requested',
            'created': 'nodate',
            'modified': 'nodate',
            'description': 'nondescript',
            'comments': 'nocomment',
            'watchers': None,
            }

    basic_kwargs = {
            'pushmaster': False,
            'web_hooks': {
                'service_name': 'noname',
                'get_request_url': 'non://existent',
                },
            'cherry_string': '',
            'expand': False,
            'push_buttons': False,
            'edit_buttons': False,
            'show_ago': False,
            'tags': None,
            'show_state_inline': False,
            'review': None,
            'repo_url': 'non://existent',
            'branch_url': 'non://existent',
            'create_time': 'nodate'
            }


    def render_module_request_with_users(self, request, request_user, current_user, **kwargs):
        """Provide enough information to render modules/request"""
        request['user'] = request_user

        return self.render_etree(self.request_page,
            current_user=current_user,
            request=request,
            **kwargs
        )

    def assert_button_link(self, button, tree, text=None, num=1):
        classname = '%s-request' % button.lower()
        if text is None:
            text = button.capitalize()

        buttons = []
        for button in tree.iter('button'):
            if button.attrib['class'] == classname:
                T.assert_equal(text, button.text)
                buttons.append(button)
        T.assert_equal(num, len(buttons))

    def test_include_request_info(self):
        tree = self.render_module_request_with_users(self.basic_request,'testuser', 'testuser', **self.basic_kwargs)

        found_ul = []
        for ul in tree.iter('ul'):
            if ul.attrib['class'] == 'request-info-inline':
                found_ul.append(ul)

        T.assert_equal(1, len(found_ul))

    def test_request_info_user_title(self):
        request = dict(self.basic_request)
        request['watchers'] = 'watcher1, watcher2'

        tree = self.render_etree(self.request_info_page,
            request=request,
            show_ago=False,
            tags=None,
            show_state_inline=False)

        # user names are listed in the first li of the list
        # <ul><li><span>title</span></li> ... </ul>
        title = list(tree.iter('li'))[0][0].text

        T.assert_equal(title, '%s (%s)' % (request['user'], request['watchers']))


if __name__ == '__main__':
    T.run()
