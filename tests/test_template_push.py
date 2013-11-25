import time

from core.settings import Settings
import testing as T

class PushTemplateTest(T.TemplateTestCase):

    authenticated = True
    push_page = 'push.html'
    push_status_page = 'push-status.html'
    push_info_page = 'push-info.html'
    push_button_bar_page = 'push-button-bar.html'
    push_dialogs_page = 'push-dialogs.html'

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
            'stageenv': None,
        }

    basic_kwargs = {
            'page_title': 'fake_push_title',
            'push_contents': {},
            'available_requests': [],
            'fullrepo': 'not/a/repo',
            'override': False,
            'push_survey_url': None
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

    def test_include_push_survey_exists(self):
        push = dict(self.basic_push)
        push['state'] = 'live'

        kwargs = dict(**self.basic_kwargs)
        kwargs['push_survey_url'] = 'http://sometestsurvey'
        tree = self.render_etree(
            self.push_page,
            push_info=push,
            **kwargs)

        for script in tree.iter('script'):
            if script.text and kwargs['push_survey_url'] in script.text:
                break
        else:
            assert False, 'push_survey_url not found'

    def test_include_new_request_form(self):
        with self.no_ui_modules():
            tree = self.render_etree(
                self.push_page,
                push_info=self.basic_push,
                **self.basic_kwargs)

        T.assert_exactly_one(
                *[mock.attrib['name'] for mock in tree.iter('mock')],
                truthy_fxn=lambda name: name == 'mock.NewRequestDialog()')

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

    def test_include_dialogs(self):
        tree = self.render_etree(
            self.push_page,
            push_info=self.basic_push,
            **self.basic_kwargs)

        found_divs = []
        for div in tree.iter('div'):
            if 'id' in div.attrib and div.attrib['id'] ==  'dialog-prototypes':
                found_divs.append(div)

        T.assert_equal(len(found_divs), 1)

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

    def test_push_info_list_items_stageenv(self):
        push = dict(self.basic_push)
        push['stageenv'] = 'stageenv'
        tree = self.render_etree(
            self.push_info_page,
            push_info=push,
            **self.basic_kwargs)

        push_info_items = dict(self.basic_push_info_items)
        push_info_items['Stage'] = 'stageenv'

        self.assert_push_info_list(list(tree.iter('ul'))[0], push_info_items)

    push_button_ids_base = ['expand-all-requests', 'collapse-all-requests', 'ping-me', 'edit-push']
    push_button_ids_pushmaster = [
            'discard-push', 'add-selected-requests',
            'remove-selected-requests', 'rebuild-deploy-branch',
            'deploy-to-stage-step0', 'deploy-to-prod', 'merge-to-master',
            'message-all', 'show-checklist']

    def test_push_buttons_random_user(self):
        with self.no_ui_modules():
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

        with self.no_ui_modules():
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

    dialog_ids = [
            'dialog-prototypes',
            'run-a-command', 'comment-on-request', 'merge-requests',
            'merge-branches-command', 'push-checklist', 'send-message-prompt',
            'push-survey', 'set-stageenv-prompt',
    ]

    def test_dialogs_divs(self):
        tree = self.render_etree(
            self.push_dialogs_page,
            push_info=self.basic_push,
            **self.basic_kwargs)

        found_divs = []
        for div in tree.iter('div'):
            T.assert_in(div.attrib['id'], self.dialog_ids)
            found_divs.append(div)

        T.assert_equal(len(found_divs),len(self.dialog_ids))


if __name__ == '__main__':
    T.run()
