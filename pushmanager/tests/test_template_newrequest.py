from pushmanager.testing.testservlet import TemplateTestCase
import pushmanager.testing as T

class NewRequestTemplateTest(TemplateTestCase):

    authenticated = True
    newrequest_page = 'modules/newrequest.html'

    form_elements = ['title', 'tags', 'review', 'repo', 'branch', 'description', 'comments', 'watchers', 'takeover']

    def test_request_form_labels(self):
        tree = self.render_etree(self.newrequest_page)

        form_attr = ['request-form-%s' % elem for elem in self.form_elements]
        form_attr_with_id = ['takeover']

        found_labels = []
        for label in tree.iter('label'):
            found_labels.append(label.attrib['for'])
            if label.attrib['for'] in form_attr_with_id:
                T.assert_equal(label.attrib['id'], '%s-label' % label.attrib['for'])

        T.assert_sorted_equal(form_attr, found_labels)

    def test_request_form_input(self):
        tree = self.render_etree(self.newrequest_page)

        id_attr = ['request-form-%s' % elem for elem in self.form_elements]
        name_attr = ['request-%s' % elem for elem in self.form_elements]

        found_id = []
        found_name = []
        for field in tree.iter('input'):
            if 'type' not in field.attrib or field.attrib['type'] in ['checkbox']:  # ignore hidden/submit
                found_id.append(field.attrib['id'])
                found_name.append(field.attrib['name'])

        for textarea in tree.iter('textarea'):
            found_id.append(textarea.attrib['id'])
            found_name.append(textarea.attrib['name'])

        T.assert_sorted_equal(id_attr, found_id)
        T.assert_sorted_equal(name_attr, found_name)

    tags = ['feature', 'fix' ,'cleanup', 'buildbot', 'caches', 'pushplans',
        'special', 'urgent', 'l10n', 'l10n-only', 'hoods', 'stagea', 'stageb',
        'no-verify']

    def test_request_quicktags(self):
        tree = self.render_etree(self.newrequest_page)

        found_tags = []
        for span in tree.iter('span'):
            if span.attrib['class'] == 'tag-suggestion':
                found_tags.append(span.text)

        T.assert_sorted_equal(self.tags, found_tags)


if __name__ == '__main__':
    T.run()
