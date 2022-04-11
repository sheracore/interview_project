import email
from email import parser
import imaplib
import poplib
from time import sleep
import tempfile
from django.core import files
from django.db import transaction
from core.utils.files import discover_mimetype
from agents.exceptions import AVException

import logging

logger = logging.getLogger(__name__)


class EmailProtocolError(Exception):
    pass


class EmailAuthenticationError(Exception):
    pass


def save_email_file(file_name, file_content):
    temp_file = tempfile.NamedTemporaryFile()
    temp_file.write(file_content)
    temp_file.flush()
    file = files.File(temp_file, name=file_name)
    return file


def create_from_email(session, part):
    from core.models.system import System
    from scans.models.file import File, FileInfo
    file_name = part.get_filename()
    file_content = part.get_payload(decode=True)
    if not (file_name or file_content):
        raise AVException('Invalid file!!!')

    file = save_email_file(file_name, file_content)
    system_settings = System.get_settings()
    try:
        allowed_mimetypes = system_settings['mimetypes']
        max_file_size = system_settings['max_file_size']
        mimetype = discover_mimetype(file)
        mimetype_not_allowed = allowed_mimetypes and (
                    mimetype not in allowed_mimetypes)
        size_not_allowed = max_file_size and (not file.size <= max_file_size)

        if mimetype_not_allowed:
            msg = f'The Uploaded file mimetype {mimetype} is not valid.'
        elif size_not_allowed:
            msg = f'The uploaded file size exceeded {max_file_size}.'
        if mimetype_not_allowed or size_not_allowed:
            with transaction.atomic():
                info = FileInfo.objects.create(size=file.size,
                                               mimetype=mimetype)
                instance = File.objects.create(
                    file=None, session=session,
                    info=info, display_name=file.name,
                    notes=msg, deleted=True, progress=100,
                )
                instance.session.update_progress()
        info = FileInfo.objects.create(size=file.size, mimetype=mimetype)
        instance = File.objects.create(
            file=file, info=info, display_name=file.name,
            session=session, valid=True
        )
        instance.update_scan_state()
        instance.session.update_progress()
        instance.set_file_info()
        instance.scan()
    except Exception as ex:
        raise AVException(str(ex))


def manage_email_parts(parts, sender, total_paths):
    from scans.models.session import Session
    counter = 0
    session = Session.objects.create(source='email', remote_addr=sender,
                                     total=total_paths, counter=counter,
                                     analyze_progress=0)
    for part in parts:
        if part.get_content_maintype() == 'multipart':
            continue
        if part.get('Content-Disposition') is None:
            continue
        counter += 1
        Session.objects.filter(pk=session.pk).update(
            total=total_paths,
            counter=counter,
            analyze_progress=round(100 * counter / total_paths, 1)
        )
        create_from_email(session, part)


class EmailBackend:

    def __init__(self, host, port, user, password):
        self.host = host
        self.port = port
        self.user = user
        self.password = password

    def login(self):
        raise NotImplementedError

    def fetch_messages(self):
        raise NotImplementedError


class ImapBackend(EmailBackend):

    def login(self):
        self.conn = imaplib.IMAP4(self.host, self.port)
        try:
            rv, data = self.conn.login(self.user, self.password)
            self.conn.select()
        except imaplib.IMAP4.error as e:
            raise EmailAuthenticationError(str(e))
        if rv != 'OK':
            raise EmailAuthenticationError('Invalid email login credentials')
        return self.conn

    def fetch_messages(self):
        logger.info('Fetching messages.')
        status, messages = self.conn.search(None, '(UNSEEN)')
        if status != 'OK':
            raise EmailAuthenticationError(
                'Can not access to unread message!!!')
        for num in messages[0].split():
            rv, message_parts = self.conn.fetch(num, '(RFC822)')
            if rv != 'OK':
                continue
            email_body = message_parts[0][1]
            mail = email.message_from_bytes(email_body)
            total_paths = email_body.count(b'filename')
            sender = mail.get('from', '').split()[-1].replace('<',
                                                              '').replace(
                '>', '')
            manage_email_parts(mail.walk(), sender, total_paths)
            self.conn.store(num, '+FLAGS', r'\Seen')


class Pop3Backend(EmailBackend):
    def login(self):
        try:
            conn = poplib.POP3(self.host, self.port, 60)
            conn.user(self.user)
            conn.pass_(self.password)
            return conn
        except poplib.error_proto as e:
            raise EmailAuthenticationError(str(e))

    def fetch_messages(self):
        conn = self.login()
        logger.info('Fetching messages.')
        messages_count = conn.stat()[0]
        for email_index in range(1, messages_count + 1):
            (resp_message, lines, octets) = conn.retr(email_index)
            msg_content = b'\r\n'.join(lines).decode('utf-8')
            msg = parser.Parser().parsestr(msg_content)
            sender = msg.get('From', '').split()[-1].replace('<',
                                                             '').replace(
                '>', '')
            if msg.is_multipart():
                parts = msg.get_payload()
                total_paths = msg.as_string().count('filename')
                manage_email_parts(parts, sender, total_paths)
            conn.dele(email_index)


class EmailScanner:

    def __init__(self, protocol, host, port, user, password):
        if protocol.lower() == 'imap':
            self.backend = ImapBackend(host, port, user, password)
        elif protocol.lower() == 'pop3':
            self.backend = Pop3Backend(host, port, user, password)
        else:
            raise EmailProtocolError('Invalid protocol')
