import imaplib
import email
from core.models.system import System
from agents.exceptions import AVException
from scans.email.utils import manage_email_parts

import logging
logger = logging.getLogger(__name__)


class Imap:

    def login_mail(self):
        system_settings = System.get_settings()
        server = system_settings.get('email_host')
        user = system_settings.get('email_user')
        password = System.decrypt_password(system_settings.get('email_password'))
        imap_port = system_settings.get('email_imap_port')

        try:
            conn = imaplib.IMAP4(server, imap_port)
            rv, data = conn.login(user, password)
        except imaplib.IMAP4.error:
            raise AVException('LOGIN FAILED!!!')
        if rv != 'OK':
            raise AVException('LOGIN FAILED!!!')
        return conn

    def get_and_save_attachment(self, conn):
        conn.select()
        status, messages = conn.search(None, '(UNSEEN)')
        if status != 'OK':
            raise AVException('Can not access to unread message!!!')
        for num in messages[0].split():
            rv, message_parts = conn.fetch(num, '(RFC822)')
            if rv != 'OK':
                continue
            email_body = message_parts[0][1]
            mail = email.message_from_bytes(email_body)
            total_paths = email_body.count(b'filename')
            sender = mail.get('from', '').split()[-1].replace('<', '').replace('>', '')
            manage_email_parts(mail.walk(), sender, total_paths)
            conn.store(num, '+FLAGS', r'\Seen')


def imap_process():
    logger.info('Starting IMAP Process...')
    imap_obj = Imap()
    conn = imap_obj.login_mail()
    logger.info('IMAP Login success')
    imap_obj.get_and_save_attachment(conn)
    conn.close()
    conn.logout()
