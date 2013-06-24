import time

import testing as T

class PushTemplateTest(T.TemplateTestCase):

    authenticated = True
    push_page = 'push.html'
    push_status_page = 'push-status.html'

    accepting_push_sections = ['blessed', 'verified', 'staged', 'added', 'pickme', 'requested']

    now = time.time()

    basic_push = {
            'id': 0,
            'user': 'pushmaster',
            'title': 'fake_push',
            'branch': 'deploy-fake-branch',
            'state': 'accepting',
            'pushtype': 'Regular',
            'created': now,
            'modified': now,
            'extra_pings': None,
        }

    basic_kwargs = {
            'page_title': 'fake_push_title',
            'push_contents': {},
            'available_requests': [],
            'fullrepo': 'not/a/repo',
            'override': False
            }

    basic_request = {
            'id': 0,
            'repo': 'non-existent',
            'branch': 'non-existent',
            'user': 'testuser',
            'reviewid': 0,
            'title': 'some title',
            'tags': None,
            'revision': '0' * 40,
            'state': 'requested',
            'created': now,
            'modified': now,
            'description': 'nondescript',
            'comments': 'nocomment',
            'watchers': None,
            }

    def test_include_push_status_when_accepting(self):
        tree = self.render_etree(
            self.push_page,
            push_info=self.basic_push,
            **self.basic_kwargs)

        found_h3 = []
        for h3 in tree.iter('h3'):
            T.assert_equal('status-header', h3.attrib['class'])
            T.assert_in(h3.attrib['section'], self.accepting_push_sections)
            found_h3.append(h3)

        T.assert_equal(len(self.accepting_push_sections), len(found_h3))

    def test_include_push_status_when_done(self):
        push = dict(self.basic_push)
        push['state'] = 'live'

        tree = self.render_etree(
            self.push_page,
            push_info=push,
            **self.basic_kwargs)

        found_h3 = []
        for h3 in tree.iter('h3'):
            T.assert_equal('status-header', h3.attrib['class'])
            found_h3.append(h3)

        T.assert_equal(1, len(found_h3))

    def generate_push_contents(self, requests):
        push_contents = dict.fromkeys(self.accepting_push_sections, [])
        for section in self.accepting_push_sections:
            push_contents[section] = requests
        return push_contents

    def test_no_mine_on_requests_as_random_user(self):
        kwargs = dict(self.basic_kwargs)
        kwargs['push_contents'] = self.generate_push_contents([self.basic_request])
        kwargs['current_user'] = 'random_user'

        with self.no_ui_modules():
            tree = self.render_etree(
                self.push_status_page,
                push_info=self.basic_push,
                **kwargs)

        found_mockreq = []
        for mockreq in tree.iter('mock'):
            T.assert_not_in('class', mockreq.getparent().attrib.keys())
            found_mockreq.append(mockreq)

        T.assert_equal(5, len(found_mockreq))

    def test_mine_on_requests_as_request_user(self):
        request = dict(self.basic_request)
        request['user'] = 'notme'

        push_contents = {}
        section_id = []
        for section in self.accepting_push_sections:
            push_contents[section] = [self.basic_request, request]
            section_id.append('%s-items' % section)

        kwargs = dict(self.basic_kwargs)
        kwargs['push_contents'] = push_contents
        kwargs['current_user'] = 'testuser'

        with self.no_ui_modules():
            tree = self.render_etree(
                self.push_status_page,
                push_info=self.basic_push,
                **kwargs)

        found_li = []
        found_mockreq = []
        for mockreq in tree.iter('mock'):
            if 'class' in mockreq.getparent().attrib:
                T.assert_equal('mine', mockreq.getparent().attrib['class'])
                found_li.append(mockreq)
            found_mockreq.append(mockreq)

        T.assert_equal(5, len(found_li))
        T.assert_equal(10, len(found_mockreq))

    def test_mine_on_requests_as_watcher(self):
        request = dict(self.basic_request)
        request['watchers'] = 'watcher1'

        push_contents = {}
        section_id = []
        for section in self.accepting_push_sections:
            push_contents[section] = [request, self.basic_request]
            section_id.append('%s-items' % section)

        kwargs = dict(self.basic_kwargs)
        kwargs['push_contents'] = push_contents
        kwargs['current_user'] = 'watcher1'

        with self.no_ui_modules():
            tree = self.render_etree(
                self.push_status_page,
                push_info=self.basic_push,
                **kwargs)

        found_li = []
        found_mockreq = []
        for mockreq in tree.iter('mock'):
            if 'class' in mockreq.getparent().attrib:
                T.assert_equal('mine', mockreq.getparent().attrib['class'])
                found_li.append(mockreq)
            found_mockreq.append(mockreq)

        T.assert_equal(5, len(found_li))
        T.assert_equal(10, len(found_mockreq))

    def test_mine_on_requests_as_pushmaster(self):
        push_contents = {}
        section_id = []
        for section in self.accepting_push_sections:
            push_contents[section] = [self.basic_request]
            section_id.append('%s-items' % section)

        kwargs = dict(self.basic_kwargs)
        kwargs['push_contents'] = push_contents

        with self.no_ui_modules():
            tree = self.render_etree(
                self.push_status_page,
                push_info=self.basic_push,
                **kwargs)

        found_mockreq = []
        for mockreq in tree.iter('mock'):
            T.assert_not_in('class', mockreq.getparent().attrib.keys())
            found_mockreq.append(mockreq)

        T.assert_equal(5, len(found_mockreq))


if __name__ == '__main__':
    T.run()
