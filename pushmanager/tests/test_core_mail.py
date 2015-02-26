import copy
import mock
import testify as T

from pushmanager.core.settings import Settings
import pushmanager.core.mail


class MailQueueTest(T.TestCase):

    @T.setup_teardown
    def mock_smtp(self):
        with mock.patch.object(pushmanager.core.mail.MailQueue, "smtp") as mocked_smtp:
            with mock.patch.object(pushmanager.core.mail.MailQueue, "message_queue"):
                self.mocked_smtp = mocked_smtp
                self.MockedSettings = copy.deepcopy(Settings)
                yield

    def test_send_mail(self):
        recipient = "test@test.com"
        message = "test message"
        subject = "test subject"
        from_email = "fromtest@test.com"

        pushmanager.core.mail.MailQueue._send_email(recipient, message, subject, from_email)

        T.assert_equal(self.mocked_smtp.sendmail.called, True)
        self.mocked_smtp.sendmail.assert_any_call(from_email, [recipient], mock.ANY)
        self.mocked_smtp.sendmail.assert_any_call(from_email, self.MockedSettings['mail']['notifyall'], mock.ANY)

    def test_mail_notifyonly(self):
        self.MockedSettings['mail']['notifyonly'] = ['notifyme', 'notifyyou', 'notifyhim', 'notifyher']
        with mock.patch.dict(Settings, self.MockedSettings):
            recipient = "test@test.com"
            message = "test message"
            subject = "test subject"
            from_email = "fromtest@test.com"

            pushmanager.core.mail.MailQueue._send_email(recipient, message, subject, from_email)

            T.assert_equal(self.mocked_smtp.sendmail.called, True)
            self.mocked_smtp.sendmail.assert_called_once_with(
                from_email,
                self.MockedSettings['mail']['notifyonly'],
                mock.ANY,
            )

            args = self.mocked_smtp.sendmail.call_args_list[0][0]
            body = "Original recipients: %s\n\n%s" % (recipient, message)
            T.assert_equal(args[2].endswith(body), True)
