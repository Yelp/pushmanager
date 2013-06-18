# -*- coding: utf-8 -*-
import testing as T

class RequestTemplateTest(T.TemplateTestCase):

    authenticated = True
    request_page = 'modules/request.html'

    def render_module_request_with_users(self, request_user, current_user, pushmaster=False):
        """Provide enough information to render modules/request"""
        request = {
            'id': 0,
            'repo': 'non-existent',
            'branch': 'non-existent',
            'user': request_user,
            'reviewid': 0,
            'title': 'some title',
            'revision': '0' * 40,
            'state': 'requested',
            'created': 'nodate',
            'modified': 'nodate',
            'description': 'nondescript',
            'comments': 'nocomment',
        }

        web_hooks = {
            'service_name': 'noname',
            'get_request_url': 'non://existent',
        }

        return self.render_etree(self.request_page,
            pushmaster=pushmaster,
            current_user=current_user,
            request=request,
            web_hooks=web_hooks,
            cherry_string='',
            expand=False,
            push_buttons=True,
            edit_buttons=False,
            show_ago=False,
            tags=None,
            show_state_inline=False,
            review=None,
            repo_url='non://existent',
            branch_url='non://existent',
            create_time='nodate',
        )

    def assert_button_link(self, button, tree, num=1):
        classname = '%s-request' % button.lower()
        text = button.capitalize()

        buttons = []
        for button in tree.iter('button'):
            if button.attrib['class'] == classname:
                T.assert_equal(text, button.text)
                buttons.append(button)
        T.assert_equal(num, len(buttons))

    def test_module_request_verify_random_user(self):
        tree = self.render_module_request_with_users(
                'testuser', 'notme', False)
        self.assert_button_link('verify', tree, 0)

    def test_module_request_verify_pushmaster(self):
        tree = self.render_module_request_with_users(
                'testuser', 'notme', True)
        self.assert_button_link('verify', tree, 1)

    def test_module_request_verify_requester(self):
        tree = self.render_module_request_with_users(
                'testuser', 'testuser', False)
        self.assert_button_link('verify', tree, 1)


if __name__ == '__main__':
    T.run()
