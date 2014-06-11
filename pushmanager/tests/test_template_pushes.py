import testify as T

from pushmanager.testing.testservlet import TemplateTestCase


class PushesTemplateTest(TemplateTestCase):

    authenticated = True
    pushes_page = 'pushes.html'
    new_push_page = 'new-push.html'

    def render_pushes_page(self, page_title='Pushes', pushes=[], pushes_per_page=50, last_push=None):
        return self.render_etree(self.pushes_page,
            page_title=page_title,
            pushes=pushes,
            rpp=pushes_per_page,
            last_push=last_push
        )

    def test_include_new_push(self):
        tree = self.render_pushes_page()

        found_form = []
        for form in tree.iter('form'):
            if form.attrib['id'] == 'push-info-form':
                found_form.append(form)

        T.assert_equal(len(found_form), 1)


if __name__ == '__main__':
    T.run()
