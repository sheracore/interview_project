import tempfile
from django.core import files
from django.db import transaction
from core.models.system import System
from core.utils.files import discover_mimetype
from agents.exceptions import AVException
from scans.models.file import File, FileInfo
from scans.models.session import Session


def save_email_file(file_name, file_content):
    temp_file = tempfile.NamedTemporaryFile()
    temp_file.write(file_content)
    temp_file.flush()
    file = files.File(temp_file, name=file_name)
    return file


def create_from_email(session, part):
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
        mimetype_not_allowed = allowed_mimetypes and (mimetype not in allowed_mimetypes)
        size_not_allowed = max_file_size and (not file.size <= max_file_size)

        if mimetype_not_allowed:
            msg = f'The Uploaded file mimetype {mimetype} is not valid.'
        elif size_not_allowed:
            msg = f'The uploaded file size exceeded {max_file_size}.'
        if mimetype_not_allowed or size_not_allowed:
            with transaction.atomic():
                info = FileInfo.objects.create(size=file.size, mimetype=mimetype)
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
    counter = 0
    session = Session.objects.create(source='email', remote_addr=sender,
                                     total=total_paths, counter=counter, analyze_progress=0)
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
