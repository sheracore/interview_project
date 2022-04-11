import poplib
from core.models.system import System
from agents.exceptions import AVException
from scans.email.utils import manage_email_parts
from email import parser

import logging
logger = logging.getLogger(__name__)


class Pop3:

    def login_mail(self):
        system_settings = System.get_settings()
        server = system_settings.get('email_host')
        user = system_settings.get('email_user')
        password = System.decrypt_password(system_settings.get('email_password'))
        pop3_port = system_settings.get('email_pop3_port')

        try:
            conn = poplib.POP3(server, pop3_port, 60)
            conn.user(user)
            conn.pass_(password)
            return conn
        except poplib.error_proto:
            raise AVException('LOGIN FAILED!!!')
        except Exception as ex:
            raise AVException(str(ex))

    def get_and_save_attachment(self, conn):
        messages_count = conn.stat()[0]
        for email_index in range(1, messages_count+1):
            (resp_message, lines, octets) = conn.retr(email_index)
            msg_content = b'\r\n'.join(lines).decode('utf-8')
            msg = parser.Parser().parsestr(msg_content)
            sender = msg.get('From', '').split()[-1].replace('<', '').replace('>', '')
            if msg.is_multipart():
                parts = msg.get_payload()
                total_paths = msg.as_string().count('filename')
                manage_email_parts(parts, sender, total_paths)
            conn.dele(email_index)


def pop3_process():
    logger.info('Starting POP3 Process...')
    pop3_obj = Pop3()
    conn = pop3_obj.login_mail()
    logger.info('POP3 Login success')
    pop3_obj.get_and_save_attachment(conn)
    conn.quit()
