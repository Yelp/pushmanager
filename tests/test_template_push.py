import time

from core.settings import Settings
import testing as T

class PushTemplateTest(T.TemplateTestCase):

    authenticated = True
    push_page = 'push.html'
    edit_push_page = 'edit-push.html'
    push_info_page = 'push-info.html'
    push_button_bar_page = 'push-button-bar.html'

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

    basic_push_info_items = {
            'Pushmaster': basic_push['user'],
            'Branch': basic_push['branch'],
            'Buildbot Runs': 'http://%s/branch/%s' % (Settings['buildbot']['servername'], basic_push['branch']),
            'State': basic_push['state'],
            'Push Type': basic_push['pushtype'],
            'Created': time.strftime("%x %X", time.localtime(basic_push['created']))
    }

    def test_include_push_info(self):
        tree = self.render_etree(
            self.push_page,
            push_info=self.basic_push,
            **self.basic_kwargs)

        found_ul = []
        for ul in tree.iter('ul'):
            if 'id' in ul.attrib and ul.attrib['id'] == 'push-info':
                found_ul.append(ul)

        T.assert_equal(1, len(found_ul))

    def test_include_push_button_bar(self):
        tree = self.render_etree(
            self.push_page,
            push_info=self.basic_push,
            **self.basic_kwargs)

        found_ul = []
        for ul in tree.iter('ul'):
            if 'id' in ul.attrib and ul.attrib['id'] == 'action-buttons':
                found_ul.append(ul)

        T.assert_equal(1, len(found_ul))

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

    push_info_items = [
        'Pushmaster', 'Branch', 'Buildbot Runs',
        'State', 'Push Type', 'Created', 'Modified'
    ]

    def assert_push_info_list(self, list_items, push_info_items):
        for li in list_items:
            T.assert_in(li[0].text, push_info_items.keys())
            if li[0].text == 'Buildbot Runs':
                T.assert_equal(li[1][0].text, 'url')
                T.assert_equal(li[1][0].attrib['href'], push_info_items['Buildbot Runs'])
            elif li[0].text == 'State':
                T.assert_equal(li[1][0].attrib['class'], 'tags')  # Inner ul
                T.assert_equal(li[1][0][0].attrib['class'], 'tag-%s' % push_info_items['State'])  # Inner li
                T.assert_equal(li[1][0][0].text, push_info_items['State'])
            elif li[0].text == 'Push Type':
                T.assert_equal(li[1][0].attrib['class'], 'tags')  # Inner ul
                T.assert_equal(li[1][0][0].attrib['class'], 'tag-%s' % push_info_items['Push Type'])  # Inner li
                T.assert_equal(li[1][0][0].text, push_info_items['Push Type'])
            else:
                T.assert_equal(li[1].text, push_info_items[li[0].text])

        T.assert_equal(len(list_items), len(push_info_items))

    def test_push_info_list_items(self):
        tree = self.render_etree(
            self.push_info_page,
            push_info=self.basic_push,
            **self.basic_kwargs)

        self.assert_push_info_list(list(tree.iter('ul'))[0], self.basic_push_info_items)

    def test_push_info_list_items_modified(self):
        push = dict(self.basic_push)
        push['modified'] = time.time()
        tree = self.render_etree(
            self.push_info_page,
            push_info=push,
            **self.basic_kwargs)

        push_info_items = dict(self.basic_push_info_items)
        push_info_items['Modified'] = time.strftime("%x %X", time.localtime(push['modified']))

        self.assert_push_info_list(list(tree.iter('ul'))[0], push_info_items)

    def test_push_info_list_items_notaccepting(self):
        push = dict(self.basic_push)
        push['state'] = 'live'
        tree = self.render_etree(
            self.push_info_page,
            push_info=push,
            **self.basic_kwargs)

        push_info_items = dict(self.basic_push_info_items)
        push_info_items['State'] = 'live'
        del push_info_items['Buildbot Runs']

        self.assert_push_info_list(list(tree.iter('ul'))[0], push_info_items)

    push_button_ids_base = ['expand-all-requests', 'collapse-all-requests', 'ping-me', 'edit-push']
    push_button_ids_pushmaster = [
            'discard-push', 'add-selected-requests',
            'remove-selected-requests', 'rebuild-deploy-branch',
            'deploy-to-stage', 'deploy-to-prod', 'merge-to-master',
            'message-all', 'show-checklist']

    def test_push_buttons_random_user(self):
        tree = self.render_etree(
            self.push_button_bar_page,
            push_info=self.basic_push,
            **self.basic_kwargs)

        found_buttons = []
        for button in tree.iter('button'):
            T.assert_in(button.attrib['id'], self.push_button_ids_base)
            found_buttons.append(button)

        T.assert_equal(len(found_buttons), len(self.push_button_ids_base))

    def test_push_buttons_pushmaster(self):
        kwargs = dict(self.basic_kwargs)
        kwargs['current_user'] = self.basic_push['user']

        tree = self.render_etree(
            self.push_button_bar_page,
            push_info=self.basic_push,
            **kwargs)

        found_buttons = []
        for button in tree.iter('button'):
            T.assert_in(
                    button.attrib['id'],
                    self.push_button_ids_base + self.push_button_ids_pushmaster)
            found_buttons.append(button)

        T.assert_equal(
                len(found_buttons),
                len(self.push_button_ids_base + self.push_button_ids_pushmaster))


if __name__ == '__main__':
    T.run()
