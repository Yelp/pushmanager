# -*- code:utf8 -*-
import testing as T

class NewRequestTemplateTest(T.TemplateTestCase):

    authenticated = True
    newrequest_page = 'modules/newrequest.html'

    tags = ['feature', 'fix' ,'cleanup', 'buildbot', 'caches', 'pushplans',
        'special', 'urgent', 'l10n', 'l10n-only', 'hoods']

    def test_request_quicktags(self):
        tree = self.render_etree(self.newrequest_page)

        found_tags = []
        for span in tree.iter('span'):
            if span.attrib['class'] == 'tag-suggestion':
                found_tags.append(span.text)

        T.assert_sorted_equal(self.tags, found_tags)


if __name__ == '__main__':
    T.run()
