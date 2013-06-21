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

    def test_include_no_request_buttons(self):
        tree = self.render_module_request_with_users(self.basic_request, 'testuser', 'testuser', **self.basic_kwargs)

        for span in tree.iter('span'):
            T.assert_not_equal('push-request-buttons', span.attrib['class'])
            T.assert_not_equal('edit-request-buttons', span.attrib['class'])

    def test_include_push_buttons(self):
        kwargs = dict(self.basic_kwargs)
        kwargs['push_buttons'] = True

        tree = self.render_module_request_with_users(self.basic_request, 'testuser', 'testuser', **kwargs)

        found_span = []
        for span in tree.iter('span'):
            T.assert_not_equal('edit-request-buttons', span.attrib['class'])
            if span.attrib['class'] == 'push-request-buttons':
                found_span.append(span)

        T.assert_equal(1, len(found_span))

    def test_include_edit_buttons(self):
        kwargs = dict(self.basic_kwargs)
        kwargs['edit_buttons'] = True

        tree = self.render_module_request_with_users(self.basic_request, 'testuser', 'testuser', **kwargs)

        found_span = []
        for span in tree.iter('span'):
            T.assert_not_equal('push-request-buttons', span.attrib['class'])
            if span.attrib['class'] == 'edit-request-buttons':
                found_span.append(span)

        T.assert_equal(1, len(found_span))

    pushmaster_button_classes = ['add-request', 'remove-request', 'comment-request', 'pushmaster-delay-request']
    pushmaster_button_text = ['Add', 'Remove', 'Comment', 'Delay']
    push_button_classes = ['verify-request', 'pickme-request', 'unpickme-request']
    push_button_text = ['Verify', 'Pick me!', 'Don\'t pick me!']
    requester_edit_button_classes = ['edit-request', 'delay-request', 'discard-request']
    requester_edit_button_text = ['Edit', 'Delay', 'Discard']
    edit_button_classes = ['edit-request']
    edit_button_text = ['Edit']

    def assert_request_buttons(self, tree, button_classes, button_text):
        found_buttons = []
        for button in tree.iter('button'):
            T.assert_in(button.attrib['class'], button_classes)
            T.assert_in(button.text, button_text)
            found_buttons.append(button)
        T.assert_equal(len(button_classes), len(found_buttons))

    def test_request_push_buttons_as_random_user(self):
        kwargs = dict(self.basic_kwargs)
        kwargs['push_buttons'] = True

        tree = self.render_module_request_with_users(self.basic_request, 'testuser', 'notuser', **kwargs)

        buttons_found = []
        for button in tree.iter('button'):
            T.assert_not_in(button.attrib['class'], self.pushmaster_button_classes + self.push_button_classes)
            buttons_found.append(button)

        T.assert_equal(0, len(buttons_found))

    def test_request_push_buttons_as_request_user(self):
        kwargs = dict(self.basic_kwargs)
        kwargs['push_buttons'] = True

        tree = self.render_module_request_with_users(self.basic_request, 'testuser', 'testuser', **kwargs)
        self.assert_request_buttons(tree, self.push_button_classes, self.push_button_text)

    def test_request_push_buttons_as_pushmaster(self):
        kwargs = dict(self.basic_kwargs)
        kwargs['push_buttons'] = True
        kwargs['pushmaster'] = True

        tree = self.render_module_request_with_users(self.basic_request, 'testuser', 'notuser', **kwargs)
        self.assert_request_buttons(
            tree,
            self.pushmaster_button_classes + self.push_button_classes,
            self.pushmaster_button_text + self.push_button_text)

    def test_request_edit_buttons_as_random_user(self):
        kwargs = dict(self.basic_kwargs)
        kwargs['edit_buttons'] = True

        tree = self.render_module_request_with_users(self.basic_request, 'testuser', 'notuser', **kwargs)
        self.assert_request_buttons(tree, self.edit_button_classes, self.edit_button_text)

    def test_request_edit_buttons_as_request_user(self):
        kwargs = dict(self.basic_kwargs)
        kwargs['edit_buttons'] = True

        tree = self.render_module_request_with_users(self.basic_request, 'testuser', 'testuser', **kwargs)
        self.assert_request_buttons(tree, self.requester_edit_button_classes, self.requester_edit_button_text)

    def test_request_edit_buttons_as_pushmaster(self):
        kwargs = dict(self.basic_kwargs)
        kwargs['edit_buttons'] = True
        kwargs['pushmaster'] = True

        tree = self.render_module_request_with_users(self.basic_request, 'testuser', 'notuser', **kwargs)
        self.assert_request_buttons(tree, self.edit_button_classes, self.edit_button_text)


if __name__ == '__main__':
    T.run()
