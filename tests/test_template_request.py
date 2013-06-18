# -*- coding: utf-8 -*-
from servlets.pushes import PushesServlet
import testing as T


class RequestTemplateTest(T.TemplateTestCase):

    def create_servlet(self, application, request):
        return PushesServlet(application, request)

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

        self.servlet.render('modules/request.html',
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

        return str.join('', self.servlet._write_buffer)

    def gen_button_link(self, button):
        classname = '%s-request' % button.lower()
        text = button.capitalize()

        return '<button class="%s">%s</button>' % (classname, text)

    def test_module_request_verify_random_user(self):
        rendered_page = self.render_module_request_with_users(
                'testuser', 'notme', False)
        verify_button = self.gen_button_link('verify')
        T.assert_not_in(verify_button, rendered_page)

    def test_module_request_verify_pushmaster(self):
        rendered_page = self.render_module_request_with_users(
                'testuser', 'notme', True)
        verify_button = self.gen_button_link('verify')
        T.assert_in(verify_button, rendered_page)

    def test_module_request_verify_requester(self):
        rendered_page = self.render_module_request_with_users(
                'testuser', 'testuser', False)
        verify_button = self.gen_button_link('verify')
        T.assert_in(verify_button, rendered_page)


if __name__ == '__main__':
    T.run()
