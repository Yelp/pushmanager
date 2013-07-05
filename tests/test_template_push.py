import time

import testing as T

class PushTemplateTest(T.TemplateTestCase):

    authenticated = True
    push_page = 'push.html'
    edit_push_page = 'edit-push.html'

    accepting_push_sections = ['blessed', 'verified', 'staged', 'added', 'pickme', 'requested']
    now = time.time()

    basic_push = {
            'id': 0,
            'user': 'pushmaster',
            'title': 'fake_push',
            'branch': 'deploy-fake-branch',
            'stageenv': '',
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

    def test_include_edit_push(self):
        tree = self.render_etree(
            self.push_page,
            push_info=self.basic_push,
            **self.basic_kwargs)

        found_form = []
        for form in tree.iter('form'):
            if form.attrib['id'] ==  'push-info-form':
                found_form.append(form)

        T.assert_equal(len(found_form), 1)


    def test_edit_push_fields(self):
        tree = self.render_etree(
            self.edit_push_page,
            push_info=self.basic_push,
            **self.basic_kwargs)
        labels = ['push-title', 'push-branch', 'push-stageenv']
        inputs = ['push-title', 'push-branch', 'push-stageenv', 'id' ,'push-submit', 'push-cancel']

        found_labels = []
        for label in tree.iter('label'):
            T.assert_in(label.attrib['for'], labels)
            found_labels.append(label)

        T.assert_equal(len(found_labels), len(labels))

        found_inputs = []
        for input in tree.iter('input'):
            T.assert_in(input.attrib['name'], inputs)
            found_inputs.append(input)

        T.assert_equal(len(found_inputs), len(inputs))


if __name__ == '__main__':
    T.run()
