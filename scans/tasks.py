import os
import psutil
from khayyam import *
import requests
import mimetypes
import shutil
from itertools import islice
import pandas as pd
import PyPDF2
from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from celery.signals import before_task_publish, task_postrun

from django.conf import settings
from django.db import transaction
from django.db.utils import DataError
from django.utils.translation import ugettext_lazy as _
from django.core.files import File as FileWrapper
from rest_framework.exceptions import ValidationError

from core.utils.files import (discover_mimetype, discover_file_info,
                              is_archive_file,
                              extract_compressed_file_recursively,
                              download_file)
from core.models.system import System
from agents.exceptions import AVException

import logging
logger = logging.getLogger(__name__)


@before_task_publish.connect
def register_task_id(sender=None, headers=None, body=None, **kwargs):
    from scans.models.session import TaskLog
    properties = kwargs.get('properties')
    if properties:
        session_id = properties.get('session_id')
        if session_id:
            TaskLog.objects.create(session_id=session_id,
                                   task_id=headers['id'])


@task_postrun.connect
def remove_task_id(sender=None, headers=None, body=None, **kwargs):
    from scans.models.session import TaskLog
    if sender.name.startswith('scans.tasks'):
        TaskLog.objects.filter(task_id=sender.request.id).delete()


@shared_task(bind=True, name='scans.tasks.bulk_create_from_disk')
def bulk_create_from_disk(self, session_id, paths, scan=False, extract=False,
                          agent_pks=None, owner_id=None):
    from scans.models.file import File, FileInfo
    from scans.models.session import Session
    from agents.models import Agent
    from django.contrib.auth import get_user_model
    from core.models.system import System
    User = get_user_model()
    owner = User.objects.get(pk=owner_id) if owner_id else None
    session = Session.objects.get(pk=session_id)
    unpacked_paths = []
    counter = 0

    self.update_state(
        state='PROGRESS',
        meta={
            'total': 0,
            'counter': 0,
            'current_path': 'Files are being indexed...',
            'progress': 0
        }
    )
    Session.objects.filter(pk=session.pk).update(
        total=0,
        counter=0,
        current_path='Files are being indexed...',
        analyze_progress=0
    )

    for path in paths:
        if os.path.isdir(path):
            gen = os.walk(path)
            for root, dirs, files in gen:
                for file in files:
                    unpacked_paths.append(
                        os.path.join(root, file)
                    )
        else:
            unpacked_paths.append(path)

    unpacked_paths = list(set(unpacked_paths))
    total_paths = len(unpacked_paths)

    if not total_paths:
        Session.objects.filter(pk=session.pk).update(
            total=total_paths,
            counter=0,
            analyze_progress=100,
            progress=100
        )
        return {
            'total': total_paths,
            'counter': 0,
            'current_path': None,
            'progress': 100
        }

    system_settings = System.get_settings()

    for path in unpacked_paths:
        counter += 1
        self.update_state(
            state='PROGRESS',
            meta={
                'total': total_paths,
                'counter': counter,
                'current_path': path,
                'progress': round(100 * counter / total_paths, 1)
            }
        )
        Session.objects.filter(pk=session.pk).update(
            total=total_paths,
            counter=counter,
            current_path=path,
            analyze_progress=round(100 * counter / total_paths, 1)
        )
        try:
            with open(path, 'rb') as f:
                f = FileWrapper(f)
                f.name = os.path.split(f.name)[-1]
                allowed_mimetypes = system_settings['mimetypes']
                max_file_size = system_settings['max_file_size']
                mimetype = discover_mimetype(f)
                mimetype_not_allowed = allowed_mimetypes and (
                            mimetype not in allowed_mimetypes)
                size_not_allowed = max_file_size and (
                    not f.size <= max_file_size)

                if mimetype_not_allowed:
                    msg = f'The Uploaded file mimetype {mimetype} is not valid.'
                elif size_not_allowed:
                    msg = f'The uploaded file size exceeded {max_file_size}.'
                if mimetype_not_allowed or size_not_allowed:
                    with transaction.atomic():
                        info = FileInfo.objects.create(size=f.size,
                                                       mimetype=mimetype)
                        instance = File.objects.create(
                            user=owner, file=None, session=session,
                            info=info, display_name=f.name,
                            notes=msg, deleted=True, progress=100,
                        )
                        instance.session.update_progress()
                    continue

                info = FileInfo.objects.create(size=f.size, mimetype=mimetype)
                instance = File.objects.create(
                    user=owner, file=f, info=info, display_name=f.name,
                    session=session, valid=True
                )
                instance.update_scan_state()
                instance.session.update_progress()
                instance.set_file_info()
                if scan:
                    if agent_pks:
                        agents = Agent.objects.filter(pk__in=agent_pks)
                    else:
                        agents = None
                    instance.scan(extract=extract, agents=agents)

                elif extract:
                    instance.extract()
        except FileNotFoundError:
            instance = File.objects.create(
                user=owner, file=None, session=session,
                display_name=os.path.split(path)[-1],
                notes=f'No such file or directory: "{path}"', deleted=True,
                progress=100
            )
            instance.session.update_progress()

        except DataError as e:
            instance = File.objects.create(
                user=owner, file=None, session=session,
                display_name=os.path.split(path)[-1],
                notes=f'{str(e)}: "{path}"', deleted=True, progress=100
            )
            instance.session.update_progress()

    Session.objects.filter(pk=session.pk).update(current_path=None)

    return {
        'total': total_paths,
        'counter': counter,
        'current_path': None,
        'progress': round(100 * counter / total_paths, 1)
    }


@shared_task(bind=True, name='scans.tasks.create_from_path')
def create_from_path(self, session_id, path, scan=False, extract=False,
                     agent_pks=None,
                     owner_id=None):
    from scans.models.file import File, FileInfo
    from scans.models.session import Session
    from core.models.system import System
    from agents.models import Agent
    from django.contrib.auth import get_user_model
    User = get_user_model()
    owner = User.objects.get(pk=owner_id) if owner_id else None
    session = Session.objects.get(pk=session_id)

    try:
        size = os.path.getsize(os.path.join(settings.MEDIA_ROOT, path))
    except OSError as e:
        raise ValidationError(str(e))

    system_settings = System.get_settings()

    max_file_size = system_settings['max_file_size']
    if max_file_size and not size <= max_file_size:
        msg = _('The file size exceeded {size}.')
        raise ValidationError(msg.format(size=max_file_size))

    with open(os.path.join(settings.MEDIA_ROOT, path), 'rb') as f:
        mimetype = discover_mimetype(f)
        allowed_mimetypes = system_settings['mimetypes']
        if allowed_mimetypes and mimetype not in allowed_mimetypes:
            msg = _('The Uploaded file mimetype {mimetype} is not valid.')
            raise ValidationError(msg.format(mimetype=mimetype))

        info = FileInfo.objects.create(size=size, mimetype=mimetype, )
        instance = File.objects.create(
            file=path, session=session, info=info,
            user=owner, valid=True
        )
        instance.set_file_info()
        if scan:
            if agent_pks:
                agents = Agent.objects.filter(pk__in=agent_pks)
            else:
                agents = None
            instance.scan(extract=extract, agents=agents)

        elif extract:
            instance.extract()

        return instance


@shared_task(bind=True, name='scans.tasks.create_from_url')
def create_from_url(self, session_id, url, save_as=None, scan=False,
                    extract=False,
                    agent_pks=None, owner_id=None):
    from scans.models.file import File, FileInfo
    from scans.models.session import Session
    from core.models.system import System
    from agents.models import Agent
    from django.contrib.auth import get_user_model

    User = get_user_model()
    owner = User.objects.get(pk=owner_id) if owner_id else None
    session = Session.objects.get(pk=session_id)

    Session.objects.filter(pk=session.pk).update(
        total=1,
        counter=0,
        current_path='Downloading...',
        analyze_progress=0
    )

    try:
        response = requests.head(url, allow_redirects=True)
    except requests.exceptions.RequestException:
        msg = 'There was an error downloading file.'
        instance = File.objects.create(
            user=owner, file=None, session=session,
            display_name=url,
            notes=msg, deleted=True
        )
        instance.file.delete(save=False)

        Session.objects.filter(pk=session.pk).update(
            total=1,
            counter=1,
            current_path=None,
            analyze_progress=100
        )
        instance.update_scan_state()
        if instance.parent:
            instance.parent.update_scan_state()
        instance.session.update_progress()
        return

    size = int(response.headers.get('content-length', 0))

    system_settings = System.get_settings()

    max_file_size = system_settings['max_file_size']

    size_not_allowed = max_file_size and not size <= max_file_size

    if size_not_allowed:
        msg = f'The uploaded file size exceeded {max_file_size}.'
        info = FileInfo.objects.create(size=size)
        instance = File.objects.create(
            user=owner, file=None, info=info, session=session,
            display_name=url,
            notes=msg, deleted=True
        )
        instance.file.delete(save=False)
        Session.objects.filter(pk=session.pk).update(
            total=1,
            counter=1,
            current_path=None,
            analyze_progress=100
        )
        instance.update_scan_state()
        if instance.parent:
            instance.parent.update_scan_state()
        instance.session.update_progress()
        return

    try:
        file = download_file(url, save_as)
    except Exception as e:
        msg = str(e)
        instance = File.objects.create(
            user=owner, file=None, session=session,
            display_name=url,
            notes=msg, deleted=True
        )
        Session.objects.filter(pk=session.pk).update(
            total=1,
            counter=1,
            current_path=None,
            analyze_progress=100
        )
        instance.file.delete(save=False)
        instance.update_scan_state()
        if instance.parent:
            instance.parent.update_scan_state()
        instance.session.update_progress()
        return

    allowed_mimetypes = system_settings['mimetypes']
    mimetype = discover_mimetype(file)
    mimetype_not_allowed = allowed_mimetypes and mimetype not in \
                           system_settings['mimetypes']

    if mimetype_not_allowed:
        msg = f'The Uploaded file mimetype {mimetype} is not valid.'
        with transaction.atomic():
            info = FileInfo.objects.create(size=file.size, mimetype=mimetype)
            instance = File.objects.create(
                user=owner, file=file, session=session, info=info,
                display_name=file.name,
                notes=msg, deleted=True
            )
            instance.file.delete(save=False)
            Session.objects.filter(pk=session.pk).update(
                total=1,
                counter=1,
                current_path=None,
                analyze_progress=100
            )
            instance.file.delete(save=False)
            instance.update_scan_state()
            if instance.parent:
                instance.parent.update_scan_state()
            instance.session.update_progress()
            return

    info = FileInfo.objects.create(size=file.size, mimetype=mimetype)
    instance = File.objects.create(
        user=owner, file=file, display_name=file.name, info=info,
        session=session, valid=True
    )
    Session.objects.filter(pk=session.pk).update(
        total=1,
        counter=1,
        current_path=None,
        analyze_progress=100
    )
    instance.file.delete(save=False)
    instance.update_scan_state()
    if instance.parent:
        instance.parent.update_scan_state()
    instance.session.update_progress()
    instance.set_file_info()
    if scan:
        if agent_pks:
            agents = Agent.objects.filter(pk__in=agent_pks)
        else:
            agents = None
        instance.scan(extract=extract, agents=agents)

    elif extract:
        instance.extract()


@shared_task(name='scans.tasks.set_file_info')
def set_file_info(file_id):
    from scans.models.file import File, FileInfo
    with transaction.atomic():
        instance = File.objects.select_for_update().get(pk=file_id)
        if not instance.deleted:
            file_info = discover_file_info(instance.file)
            allow_extensions = mimetypes.guess_all_extensions(
                instance.info.mimetype)
            extension = os.path.splitext(instance.file.name)[1][1:].lower()

            ext_match = True
            if allow_extensions and extension not in allow_extensions:
                ext_match = False
            if instance.info:
                instance.info.update(**file_info, extension=extension,
                                     ext_match=ext_match)
            else:
                if instance.info:
                    instance.info.update(**file_info, extension=extension,
                                         ext_match=ext_match)
                else:
                    info = FileInfo.objects.create(**file_info,
                                                   extension=extension,
                                                   ext_match=ext_match)
                    instance.info = info
                    instance.save(update_fields=['info'])


@shared_task(name='scans.tasks.extract_file')
def extract_file(file_id):
    from scans.models.file import File, FileInfo
    from core.models.system import System

    with transaction.atomic():
        instance = File.objects.select_for_update().get(pk=file_id)
        if instance.deleted:
            instance.update(notes='File has been deleted.')
            return []
        else:

            children = instance.children.all()

            if children.exists():
                return children

            print(
                f'Extracting File (ID={file_id}) {instance.display_name}')
            try:
                extracted_path = extract_compressed_file_recursively(
                    instance.file.path
                )
            except Exception as e:
                instance.update(notes=str(e))
                return []

    system_settings = System.get_settings()
    tree = System.walk_path_recursively(extracted_path)
    files = []
    allowed_mimetypes = system_settings['mimetypes']

    for item in tree:
        with open(item, 'rb') as f:
            f = FileWrapper(f)
            mimetype = discover_mimetype(f)
            mimetype_not_allowed = allowed_mimetypes and (
                        mimetype not in allowed_mimetypes)
            if mimetype_not_allowed:
                msg = f'The Uploaded file mimetype {mimetype} is not valid.'
                with transaction.atomic():
                    info = FileInfo.objects.create(size=f.size,
                                                   mimetype=mimetype)
                    File.objects.create(
                        session=instance.session,
                        info=info,
                        parent=instance,
                        user=instance.user,
                        file=None,
                        display_name=os.path.split(f.name)[-1],
                        notes=msg, deleted=True
                    )
                    continue
            info = FileInfo.objects.create(size=f.size, mimetype=mimetype)
            file = File(parent=instance, user=instance.user, valid=True,
                        file=item, info=info, session=instance.session,
                        display_name=os.path.split(f.name)[-1])
            files.append(file)

    instances = []
    generator = iter(files)
    batch_size = 100
    while True:
        items = list(islice(generator, batch_size))
        if not items:
            break
        instances += File.objects.bulk_create(items, batch_size)
    for child in instances:
        child.set_file_info()

    return instances


@shared_task(name='scans.tasks.perform_scan', soft_time_limit=60)
def perform_scan(scan_id):
    from scans.models.scan import Scan

    logger.info(f'Starting to scan ID {scan_id}')

    instance = Scan.objects.select_related('file').get(pk=scan_id)

    try:
        if instance.file.file:
            try:
                stdout, scan_time, infected_num, threats = instance.agent.av.scan(
                    instance.file.file.path)
                instance.update(status_code=200,
                                stdout=stdout,
                                scan_time=scan_time,
                                infected_num=infected_num)
            except ModuleNotFoundError as e:
                instance.update(status_code=404,
                                error=str(e))
            except AVException as e:
                instance.update(status_code=498,
                                error=str(e))
            except (TimeoutError, OSError, EOFError) as e:
                instance.update(status_code=499,
                                error=str(e))

        else:
            instance.update(status_code=499,
                            error='Source file does not exist')

    except SoftTimeLimitExceeded as e:
        logger.info(f'Job of scan ID {scan_id} timed out.')
        instance.update(status_code=499,
                        error=str(e))
    finally:
        instance.file.update_scan_state()
        if instance.file.parent:
            instance.file.parent.update_scan_state()
        instance.file.session.update_progress()
        instance.log()


@shared_task(name='scans.tasks.scan_file')
def scan_file(file_id, _async=True, extract=False, agent_pks=None):
    from scans.models.file import File
    from scans.models.scan import Scan
    from agents.models import Agent

    instance = File.objects.get(pk=file_id)

    if extract and is_archive_file(instance.file.path):
        children = instance.children.all()
        if not children.exists():
            children = extract_file(file_id)

        if children:
            files_to_scan = children
        else:
            if instance.notes:
                files_to_scan = []
            else:
                files_to_scan = [instance]
    else:
        files_to_scan = [instance]

    if agent_pks:
        queryset = Agent.objects.filter(active=True, pk__in=agent_pks)
    else:
        queryset = Agent.objects.filter(active=True)

    if files_to_scan:
        agents_exist = queryset.count()

        for file_to_scan in files_to_scan:
            if file_to_scan.deleted or not file_to_scan.valid:
                continue
            if agents_exist:
                scans = []
                for agent in queryset:
                    scan = Scan(file=file_to_scan, agent=agent,
                                av_name=agent.av_name)
                    scans.append(scan)

                scan_instances = Scan.objects.bulk_create(scans)
                file_to_scan.update_scan_state()
                instance.session.update_progress()

                for scan in scan_instances:
                    scan.perform(_async=_async)
            else:
                File.objects.filter(pk=instance.pk).update(progress=100,
                                                           notes='No scanner found')
                instance.session.update_progress()
    else:
        File.objects.filter(pk=instance.pk).update(progress=100)
        instance.session.update_progress()


@shared_task(bind=True, name='scans.tasks.postscan_print')
def postscan_print(self, session_id):
    from scans.models.file import File
    from scans.models.session import Session

    self.update_state(
        state='PROGRESS',
        meta={
            'title': _('Printing scan results receipt')
        }
    )

    session = Session.objects.get(pk=session_id)

    total_files = File.objects.filter(
        session=session, parent=None
    )
    infected_files = total_files.filter(infected=True)
    clean_files = total_files.filter(infected=False)
    total_files_count = total_files.count()
    infected_files_count = infected_files.count()
    clean_files_count = clean_files.count()
    # local_dt = timezone.localtime(session.created_at)
    # scan_date_time = local_dt.strftime('%m/%d/%y, %H:%M:%S')
    scan_date_time = JalaliDatetime.now().strftime('%Y/%m/%d, %H:%M:%S')

    values = {
        'date_time': scan_date_time,
        'total_count': total_files_count,
        'infected_count': infected_files_count,
        'clean_count': clean_files_count,
        'av_names': ','.join(
            list(set(
                total_files.exclude(
                    scans=None
                ).values_list('scans__agent__av_name', flat=True)
            ))
        ),
        'infected_files': ','.join(infected_files.values_list(
            'display_name', flat=True))
    }

    base64_pdf = System.generate_pdf_scan_result(**values)
    System.print_receipt(base64_pdf)


@shared_task(bind=True, name='scans.tasks.postscan_copy')
def postscan_copy(self, session_id, path):
    from scans.models.file import File
    from scans.models.session import Session
    counter = 0

    self.update_state(
        state='PROGRESS',
        meta={
            'total': 0,
            'counter': counter,
            'current_path': _('Files are being indexed...'),
            'progress': 0
        }
    )

    session = Session.objects.get(pk=session_id)

    clean_files = File.objects.filter(
        session=session).filter(parent=None, infected=False)
    count = clean_files.count()

    if not count:
        raise Exception(_('No clean file found'))
        # return {
        #     'total': count,
        #     'counter': counter,
        #     'current_path': 'No clean file found',
        #     'progress': 100
        # }

    psutil_partitions = psutil.disk_partitions()
    devname = None
    for p in psutil_partitions:
        if p.mountpoint == path:
            devname = p.device
    if not devname:
        raise Exception(f'Device not found for mount point "{path}"')

    dst_dir = os.path.join(path, JalaliDatetime.now().strftime(
        f'%Y_%m_%d_{str(session_id)}'))

    if not os.path.exists(dst_dir):
        os.makedirs(dst_dir)

    print(f'Starting to copy {count} files to {dst_dir}')

    for file in clean_files:
        counter += 1
        dst_path = os.path.join(dst_dir, file.display_name or
                                os.path.split(file.file.path)[-1])
        shutil.copyfile(file.file.path, dst_path)
        print(f'Copied {file.file.path} to {dst_path}')

        self.update_state(
            state='PROGRESS',
            meta={
                'total': count,
                'counter': counter,
                'current_path': file.file.path,
                'progress': round(100 * counter / count, 1)
            }
        )

    self.update_state(
        state='PROGRESS',
        meta={
            'total': count,
            'counter': counter,
            'current_path': _('Finishing copy ...'),
            'progress': round(100 * counter / count, 1)
        }
    )
    System.unmount(devname)
    # System.mount(devname, path)


@shared_task(bind=True, name='scans.tasks.postscan_ftp')
def postscan_ftp(self, session_id):
    from scans.models.file import File
    from scans.models.session import Session
    from core.models.system import System
    from ftplib import FTP

    counter = 0

    self.update_state(
        state='PROGRESS',
        meta={
            'total': 0,
            'counter': counter,
            'current_path': _('Files are being indexed...'),
            'progress': 0
        }
    )

    session = Session.objects.get(pk=session_id)

    clean_files = File.objects.filter(
        session=session).filter(parent=None, infected=False)

    count = clean_files.count()

    if not count:
        raise Exception(_('No clean file found'))
        # return {
        #     'total': 0,
        #     'counter': counter,
        #     'current_path': 'No clean file found',
        #     'progress': 100
        # }

    settings_ = System.get_settings()
    ftp_host = settings_['ftp_host']
    ftp_user = settings_['ftp_user']
    ftp_pass = System.decrypt_password(settings_['ftp_pass'])
    ftp_port = settings_['ftp_port']
    ftp = FTP()
    ftp.encoding = 'utf-8'
    ftp.connect(ftp_host, port=ftp_port, timeout=5)
    ftp.login(ftp_user, ftp_pass)

    directory = JalaliDatetime.now().strftime(f'%Y_%m_%d_{str(session_id)}')
    if directory in ftp.nlst():
        ftp.cwd(directory)

    else:
        ftp.mkd(directory)
        ftp.cwd(directory)

    print(f'Starting to copy {count} files to FTP host {ftp_host}')

    try:
        for file in clean_files:
            f = open(file.file.path, 'rb')
            file_name = file.display_name or os.path.split(file.file.path)[-1]
            ftp.storbinary(f"STOR {file_name}", f)
            f.close()
            counter += 1
            self.update_state(
                state='PROGRESS',
                meta={
                    'total': count,
                    'counter': counter,
                    'current_path': file.file.path,
                    'progress': round(100 * counter / count, 1)
                }
            )
            print(f'Copied {file.file.path} to {ftp.pwd()}/{file_name}')
    finally:
        ftp.quit()


@shared_task(bind=True, name='scans.tasks.postscan_sftp')
def postscan_sftp(self, session_id):
    from scans.models.file import File
    from scans.models.session import Session
    from core.models.system import System
    import pysftp

    counter = 0

    self.update_state(
        state='PROGRESS',
        meta={
            'total': 0,
            'counter': counter,
            'current_path': _('Files are being indexed...'),
            'progress': 0
        }
    )

    session = Session.objects.get(pk=session_id)

    clean_files = File.objects.filter(
        session=session).filter(parent=None, infected=False)

    if not clean_files.exists():
        raise Exception(_('No clean file found'))

    settings_ = System.get_settings()
    sftp_host = settings_['sftp_host']
    sftp_user = settings_['sftp_user']
    sftp_pass = System.decrypt_password(settings_['sftp_pass'])
    sftp_port = settings_['sftp_port']
    cnopts = pysftp.CnOpts()
    cnopts.hostkeys = None
    sftp = pysftp.Connection(host=sftp_host, username=sftp_user,
                             port=sftp_port,
                             password=sftp_pass, cnopts=cnopts)

    directory = JalaliDatetime.now().strftime(f'%Y_%m_%d_{str(session_id)}')
    if directory in sftp.listdir():
        sftp.chdir(directory)

    else:
        sftp.mkdir(directory)
        sftp.chdir(directory)

    count = clean_files.count()

    print(f'Starting to copy {count} files to SFTP host {sftp_host}')

    try:
        for file in clean_files:
            file_name = file.display_name or os.path.split(file.file.path)[-1]
            sftp.put(localpath=file.file.path, remotepath=file_name)

            counter += 1
            self.update_state(
                state='PROGRESS',
                meta={
                    'total': count,
                    'counter': counter,
                    'current_path': file.file.path,
                    'progress': round(100 * counter / count, 1)
                }
            )
            print(f'Copied {file.file.path} to {sftp.getcwd()}/{file_name}')
    finally:
        sftp.close()


@shared_task(bind=True, name='scans.tasks.postscan_webdav')
def postscan_webdav(self, session_id, username=None, password=None):
    from webdav3.client import Client
    from scans.models.file import File
    from scans.models.session import Session
    from core.models.system import System

    counter = 0

    self.update_state(
        state='PROGRESS',
        meta={
            'total': 0,
            'counter': counter,
            'current_path': _('Files are being indexed...'),
            'progress': 0
        }
    )

    session = Session.objects.get(pk=session_id)

    clean_files = File.objects.filter(
        session=session).filter(parent=None, infected=False)

    count = clean_files.count()

    if not count:
        raise Exception(_('No clean file found'))

    settings_ = System.get_settings()
    if username and password:
        webdav_host = f'{settings_.get("webdav_host")}/{username}'
        webdav_user = username
        webdav_pass = password
    else:
        webdav_host = f'{settings_.get("webdav_host")}/{settings_.get("webdav_user")}'
        webdav_user = settings_.get("webdav_user")
        webdav_pass = System.decrypt_password(settings_.get('webdav_pass'))
    options = {
        'webdav_hostname': webdav_host,
        'webdav_login': webdav_user,
        'webdav_password': webdav_pass
    }
    client = Client(options)
    client.verify = False  # To not check SSL certificates (Default = True)
    directory = JalaliDatetime.now().strftime(f'%Y_%m_%d_{str(session_id)}')
    if f'{directory}/' not in client.list():
        client.mkdir(directory)
    print(
        f'Starting to copy {count} files to WebDav host {options["webdav_hostname"]}')
    for file in clean_files:
        file_name = file.display_name or os.path.split(file.file.path)[-1]
        client.upload_file(remote_path=f'{directory}/{file_name}',
                           local_path=file.file.path)

        counter += 1
        self.update_state(
            state='PROGRESS',
            meta={
                'total': count,
                'counter': counter,
                'current_path': file.file.path,
                'progress': round(100 * counter / count, 1)
            }
        )
        print(f'Copied {file.file.path} to {directory}/{file_name}')


@shared_task(name='scans.tasks.cleanup')
def cleanup(days_older_than):
    from scans.models.file import File
    File.objects.cleanup_disk(days_older_than)


@shared_task
def scan_report(pk_list, report_pk):
    from scans.models.scan import Scan, ScanReport

    html_string = '''
           <html>
             <head><title>HTML Pandas Dataframe with CSS</title></head>
             <style>
               .pdf-table {{
                   font-size: 11pt; 
                   font-family: Arial;
                   border-collapse: collapse;
                   border: 1px solid silver;
                   margin: auto;
               }}

               .pdf-table td, th {{
                   padding: 5px;
                   text-align: center;
                   background-color: #F5F5F5;
               }}

             </style>
             <body>
               {table}
             </body>
           </html>
           '''

    queryset = Scan.objects.filter(pk__in=pk_list)
    scan_query = queryset.values(
        'av_name',
        'scan_time',
        'infected_num',
        'created_at'
    )
    scans = []
    for scan in scan_query:
        if scan['created_at'] is None:
            scan['created_at'] = ''
        else:
            scan['created_at'] = scan['created_at'].strftime(
                '%Y-%m-%d %H:%M:%S')

        scans.append(scan)

    obj = ScanReport.objects.get(pk=report_pk)

    try:
        data_frame = pd.DataFrame(scans)
        writer = pd.ExcelWriter(f'report-{obj.pk}.xlsx', engine='xlsxwriter')
        data_frame.to_excel(writer, sheet_name='Sheet1', index=False)
        workbook = writer.book
        worksheet = writer.sheets['Sheet1']
        format1 = workbook.add_format(
            {'valign': 'vcenter', 'align': 'center', 'text_wrap': True}
        )

        worksheet.set_column('A:A', 10, format1)
        worksheet.set_column('B:E', 30, format1)
        worksheet.set_default_row(25)
        writer.save()

        pd.read_excel(f'report-{obj.pk}.xlsx').to_csv(f'report-{obj.pk}.csv',
                                                      index=False)
        tab = pd.read_excel(f'report-{obj.pk}.xlsx').to_html(
            classes='pdf-table',
            index=False)

        with open(f'report-{obj.pk}.html', 'w') as f:
            f.write(html_string.format(table=tab))

        excel_file = FileWrapper(open(f'report-{obj.pk}.xlsx', 'rb'))
        csv_file = FileWrapper(open(f'report-{obj.pk}.csv', 'rb'))
        html_file = FileWrapper(open(f'report-{obj.pk}.html', 'r'))
        pdf = PyPDF2.generate_pdf(html_file.read(), encoding='utf-8')
        with open(f'report-{obj.pk}.pdf', 'wb') as f:
            f.write(pdf)

        pdf_file = FileWrapper(open(f'report-{obj.pk}.pdf', 'rb'))
        obj.excel_file = excel_file
        obj.pdf_file = pdf_file
        obj.csv_file = csv_file
        obj.status = 'created'
        obj.error = ''
        obj.save()

    except Exception as e:
        obj.status = 'failed'
        obj.error = str(e)
        obj.save()

    finally:
        if os.path.exists(f'report-{obj.pk}.csv'):
            os.remove(f'report-{obj.pk}.csv')

        if os.path.exists(f'report-{obj.pk}.html'):
            os.remove(f'report-{obj.pk}.html')

        if os.path.exists(f'report-{obj.pk}.xlsx'):
            os.remove(f'report-{obj.pk}.xlsx')

        if os.path.exists(f'report-{obj.pk}.pdf'):
            os.remove(f'report-{obj.pk}.pdf')


@shared_task
def scan_path(path, av_name, host):
    from scans.backends import Scanner
    try:
        scanner = Scanner(av_name, host, 18811)
        stdout, scan_time, infected_num, threats = scanner.av.scan(path)
        return {
            'path': path,
            'status_code': 200,
            'stdout': stdout,
            'scan_time': scan_time,
            'infected_num': infected_num,
            'threats': threats
        }
    except (FileNotFoundError, ModuleNotFoundError, AVException, TimeoutError,
            OSError, EOFError) as e:
        return {
            'path': path,
            'status_code': 400,
            'detail': str(e),
        }


@shared_task
def save_results(results):
    return results


# @task_postrun.connect
# def scan_postrun(sender=None, headers=None, body=None, **kwargs):
#     logger.info(kwargs)
    # logger.info(kwargs['task'].name) # scans.tasks.scan_path
    # logger.info(kwargs['args'])
    # logger.info(kwargs['state'])
    # logger.info(kwargs['retval'])