import socket
import platform
from collections import defaultdict
import netifaces
from glob import glob
import yaml
import time
import rpyc
import ldap
import os
import pyudev
import psutil
import shutil
import arabic_reshaper
import base64
import pysftp
from cryptography.fernet import Fernet, InvalidToken

from reportlab.platypus import Paragraph, Image, Spacer
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from bidi.algorithm import get_display
from reportlab.lib.units import inch
from reportlab.lib import colors
from ftplib import FTP
from webdav3.client import Client

from django.conf import settings
from django.core.cache import cache
from django.utils.translation import ugettext_lazy as _

import proj
from core.exceptions import PrinterError
from core.models.email import EmailScanner, EmailProtocolError, EmailAuthenticationError
from core.utils.commanding import execute_local
from core.mimetypes import mimetypes, _mimetypes
from core.utils.interfaces import netmask_to_cidr
from core.models.mimetype import MimeTypeCat, MimeType
from core.models.printer import Printer

import logging
logger = logging.getLogger(__name__)


class System:

    @staticmethod
    def start_rpc(port=18811):
        from rpyc.utils.server import ThreadedServer
        server = ThreadedServer(rpyc.ClassicService, port=port)
        print(f'Listening on port {port}')
        server.start()

    @staticmethod
    def delete_settings():
        return cache.delete('settings')

    @staticmethod
    def get_settings():
        _settings = {
            'i_am_a_kiosk': settings.I_AM_A_KIOSK,
            'i_can_manage_kiosks': settings.I_CAN_MANAGE_KIOSKS,
            'public_scan': settings.PUBLIC_SCAN,
            'url_scan': settings.URL_SCAN,
            'version_info': {
                'number': proj.VERSION
            },
        }
        cache_settings = cache.get('settings') or {}
        _settings.update(cache_settings)
        return _settings

    @staticmethod
    def set_settings(values):
        extract = values.get('extract')
        if 'extract' in values and extract not in [False, None, True]:
            raise ValueError("Not a valid choice for extract")

        compress = values.get('compress')
        if 'compress' in values and compress not in [False, None, True]:
            raise ValueError("Not a valid choice for compress")

        delete_file_after_scan = values.get('delete_file_after_scan')
        if 'delete_file_after_scan' in values and delete_file_after_scan not in [
            False, True]:
            raise ValueError('Not a valid choice for delete_file_after_scan')

        clean_acceptance_index = values.get('clean_acceptance_index')
        if 'clean_acceptance_index' in values and not 0 < clean_acceptance_index <= 1:
            raise ValueError('Not a valid choice for clean_acceptance_index')

        valid_acceptance_index = values.get('valid_acceptance_index')
        if 'valid_acceptance_index' in values and not 0 < valid_acceptance_index <= 1:
            raise ValueError('Not a valid choice for valid_acceptance_index')

        ftp_port = values.get('ftp_port')
        if 'ftp_port' in values and not isinstance(ftp_port, int):
            raise ValueError('Not a valid choice for ftp_port')

        log = values.get('log')
        if 'log' in values and not isinstance(log, bool):
            raise ValueError('Not a valid choice for log')

        syslog = values.get('syslog')
        if 'syslog' in values and not isinstance(syslog, bool):
            raise ValueError('Not a valid choice for syslog')

        syslog_protocol = values.get('syslog_protocol')
        if syslog_protocol and syslog_protocol not in ['UDP', 'TCP']:
            raise ValueError('Not a valid choice for syslog_protocol')

        log_http_method = values.get('log_http_method')
        if log_http_method and log_http_method not in ['POST', 'PATCH']:
            raise ValueError('Not a valid choice for log_http_method')

        log_http_headers = values.get('log_http_headers')
        if log_http_headers and not isinstance(log_http_headers, dict):
            raise ValueError('Not a valid dict for log_http_headers')

        login_required = values.get('login_required')
        if 'login_required' in values and login_required not in [False, True]:
            raise ValueError('Not a valid choice for login_required')

        cache.set('settings', values, None)

        logger.info({
            'action': 'settings_create',
            'additional_data': values
        })

    @staticmethod
    def update_settings(values):
        _settings = System.get_settings()
        ldap_password = values.get('ldap_password')
        if ldap_password:
            values['ldap_password'] = System.encrypt_password(ldap_password)
        webdav_password = values.get('webdav_pass')
        if webdav_password:
            values['webdav_pass'] = System.encrypt_password(webdav_password)
        ftp_pass = values.get('ftp_pass')
        if ftp_pass:
            values['ftp_pass'] = System.encrypt_password(ftp_pass)
        sftp_pass = values.get('sftp_pass')
        if sftp_pass:
            values['sftp_pass'] = System.encrypt_password(sftp_pass)
        email_password = values.get('email_password')
        if email_password:
            values['email_password'] = System.encrypt_password(email_password)
        pincode = values.get('pincode')
        if pincode:
            values['pincode'] = System.encrypt_password(pincode)
        _settings.update(values)
        # AuditLog.objects.create(action='settings_update',
        #                         additional_data=values,
        #                         description="Settings Update")
        System.set_settings(_settings)
        logger.info({
            'action': 'settings_update',
            'additional_data': values
        })

    @staticmethod
    def reset_settings():
        values = {
            'logo': None,
            'max_file_size': 26214400,
            'total_max_files_size': 10 * 26214400,
            'mimetypes': _mimetypes,
            'extract': None,
            'compress': None,
            'ftp_host': '',
            'ftp_user': '',
            'ftp_pass': '',
            'ftp_port': 21,
            'sftp_host': '',
            'sftp_user': '',
            'sftp_pass': '',
            'sftp_port': 22,
            'webdav_host': '',
            'webdav_user': '',
            'webdav_pass': '',
            'delete_file_after_scan': False,
            'clean_acceptance_index': 0.5,
            'valid_acceptance_index': 0.5,
            'log': False,
            'log_http_url': '',
            'log_http_method': '',
            'log_http_headers': {},
            'ldap_server_uri': '',
            'ldap_bind_dn': '',
            'ldap_password': '',
            'ldap_user_search': '',
            'syslog': False,
            'syslog_ip': '',
            'syslog_port': 514,
            'syslog_protocol': 'UDP',
            'email_host': '',
            'email_user': '',
            'email_password': '',
            'email_port': 587,
            'email_imap_port': 143,
            'email_pop3_port': 110,
            'email_protocol': 'IMAP',
            'log_file_path': '',
        }
        if settings.I_AM_A_KIOSK:
            values.update({
                'pincode': System.encrypt_password('123456'),
                'printer_ip': '',
                'printer_port': '',
                'input_slots': None,
                'output_slots': None,
                'update_slots': None,
                'login_required': False
            })

        # AuditLog.objects.create(action='settings_reset',
        #                         additional_data=values,
        #                         description="Settings Reset")

        System.set_settings(values)
        logger.info({
            'action': 'settings_reset',
            'additional_data': values
        })

    @staticmethod
    def prepopulate_mimetypes():
        for item in mimetypes:
            cat = item['cat']
            cat_instance, created = MimeTypeCat.objects.get_or_create(
                name=cat)
            for mime in item['mimetypes']:
                MimeType.objects.update_or_create(
                    name=mime['mimetype'],
                    defaults={
                        'cat': cat_instance,
                        'extensions': mime['extensions']
                    }
                )

    @staticmethod
    def create_plymouth_file():
        splash_path = os.path.join(settings.STATIC_ROOT, 'core', 'splash')
        content = '[Plymouth Theme]\nName=Viruspod Logo\nDescription=A theme that features a blank background with a logo.\nModuleName=script\n\n[script]\nImageDir='
        content += splash_path
        content += '\nScriptFile='
        content += os.path.join(splash_path, 'ubuntu-logo.script')
        with open(os.path.join(splash_path, 'ubuntu-logo.plymouth'), 'w') as fh:
            fh.write(content)

    @staticmethod
    def set_splash():
        img_data = System.get_settings()['logo'] or ''
        if img_data:
            try:
                img_data = bytes(img_data.split(',')[1], 'utf-8')
                logo_path = os.path.join(settings.STATIC_ROOT, 'core',
                                         'splash')

                with open(os.path.join(logo_path, 'ubuntu-logo.png'),
                          'wb') as fh:
                    fh.write(base64.decodebytes(img_data))

                with open(os.path.join(logo_path, 'ubuntu-logo16.png'),
                          'wb') as fh:
                    fh.write(base64.decodebytes(img_data))

                # execute_local('sudo touch /boot/grub/menu.lst')
                execute_local('update-initramfs -u')
                execute_local('sudo update-grub2')
                logger.info('Splash screen image changed.')
            except Exception as e:
                logger.info(str(e))

    @staticmethod
    def get_folder_size(path):
        total_size = 0
        counter = 0
        for root, dirs, files in os.walk(path):
            for f in files:
                counter += 1
                fp = os.path.join(root, f)
                # skip if it is symbolic link
                if not os.path.islink(fp):
                    total_size += os.path.getsize(fp)

        return total_size, counter

    @staticmethod
    def get_disk_usage(mountpoint):
        stat = psutil.disk_usage(mountpoint)
        data = {
            'total': stat.total,
            'used': stat.used,
            'free': stat.free
        }
        return data

    @staticmethod
    def get_media_root_disk_usage():
        return System.get_disk_usage(settings.MEDIA_ROOT)

    @staticmethod
    def get_sys_info():
        system, node, release, version, machine, processor = platform.uname()
        mem = psutil.virtual_memory()
        data = {
            'name': system,
            'node': node,
            'release': release,
            'version': version,
            'machine': machine,
            'processor': processor,
            'disk': System.get_disk_usage('/'),
            'media': System.get_media_root_disk_usage(),
            'cpu': {
                'count': psutil.cpu_count(),
                'percent': psutil.cpu_percent()
            },
            'memory': dict(mem._asdict())
        }

        return data

    @staticmethod
    def poweroff():
        result = execute_local('shutdown now -h')
        return result

    @staticmethod
    def reboot():
        result = execute_local('reboot')
        return result

    @staticmethod
    def mount(devname, mountpoint):
        if not System.check_disk(devname):
            cache.set(
                devname,
                {
                    'status_code': 'mounting',
                    'stdout': '',
                    'stderr': ''
                },
                None
            )
            # result = execute_local(f'/usr/bin/systemd-mount --no-block -t auto --automount=yes -o iocharset=utf8 --collect {devname} {mountpoint}')
            result = execute_local(f'mount -t auto -o iocharset=utf8 {devname} {mountpoint}')
            if System.check_disk(devname):
                cache.set(
                    devname,
                    {
                        'status_code': 'mounted',
                        'stdout': result.stdout,
                        'stderr': result.stderr
                    },
                    None
                )
                # AuditLog.objects.create(action='device_mount',
                #                           additional_data={
                #                               'status_code': 'mounted',
                #                               'stdout': result.stdout,
                #                               'stderr': result.stderr
                #                           },
                #                           description='device mounted')
                logger.info({
                    'action': 'device_mount',
                    'additional_data': {
                        'status_code': 'mounted',
                        'stdout': result.stdout,
                        'stderr': result.stderr
                    }
                })
                return True
            else:
                cache.set(
                    devname,
                    {
                        'status_code': 'failed_to_mount',
                        'stdout': result.stderr,
                        'stderr': result.stderr
                    },
                    None
                )
                # AuditLog.objects.create(action='device_mount',
                #                           additional_data={
                #                               'status_code': 'failed_to_mount',
                #                               'stdout': result.stderr,
                #                               'stderr': result.stderr},
                #                           description='Mounting failed')
                logger.info({
                    'action': 'device_mount',
                    'additional_data': {
                        'status_code': 'failed_to_mount',
                        'stdout': result.stderr,
                        'stderr': result.stderr}
                })

                return False
        else:
            cache.set(
                devname,
                {
                    'status_code': 'already_mounted',
                    'stdout': '',
                    'stderr': ''
                },
                None
            )
            # AuditLog.objects.create(action='device_mount',
            #                           additional_data={
            #                               'status_code': 'already_mounted',
            #                               'stdout': '',
            #                               'stderr': ''},
            #                           description='Already Mounted')
            logger.info({
                'action': 'device_mount',
                'additional_data': {
                    'status_code': 'already_mounted',
                    'stdout': '',
                    'stderr': ''}
            })

            return True

    @staticmethod
    def unmount(devname):
        if System.check_disk(devname):
            cache.set(
                devname,
                {
                    'status_code': 'unmounting',
                    'stdout': '',
                    'stderr': ''
                },
                None
            )
            # result = execute_local(f'/usr/bin/systemd-umount {devname}')
            result = execute_local(f'umount --force {devname}')
            if not System.check_disk(devname):
                cache.set(
                    devname,
                    {
                        'status_code': 'unmounted',
                        'stdout': result.stderr,
                        'stderr': result.stderr
                    },
                    None
                )
                # AuditLog.objects.create(action='device_unmount',
                #                           additional_data={
                #                               'status_code': 'unmounted',
                #                               'stdout': result.stderr,
                #                               'stderr': result.stderr},
                #                           description='Device Unmounted')
                logger.info({
                    'action': 'device_unmount',
                    'additional_data': {
                        'status_code': 'unmounted',
                        'stdout': result.stderr,
                        'stderr': result.stderr}
                })

                return True
            else:
                cache.set(
                    devname,
                    {
                        'status_code': 'failed_to_unmount',
                        'stdout': result.stderr,
                        'stderr': result.stderr
                    },
                    None
                )
                # AuditLog.objects.create(action='device_unmount',
                #                           additional_data={
                #                               'status_code': 'failed_to_unmount',
                #                               'stdout': result.stderr,
                #                               'stderr': result.stderr},
                #                           description='Unmounting failed')
                logger.info({
                    'action': 'device_unmount',
                    'additional_data': {
                        'status_code': 'failed_to_unmount',
                        'stdout': result.stderr,
                        'stderr': result.stderr}
                })

                return False
        else:
            cache.set(
                devname,
                {
                    'status_code': 'already_unmounted',
                    'stdout': '',
                    'stderr': ''
                },
                None
            )
            # AuditLog.objects.create(action='device_unmount',
            #                           additional_data={
            #                               'status_code': 'already_unmounted',
            #                               'stdout': '',
            #                               'stderr': ''},
            #                           description='Already Unmounted')
            logger.info({
                'action': 'device_unmount',
                'additional_data': {
                    'status_code': 'already_unmounted',
                    'stdout': '',
                    'stderr': ''}
            })

            return True

    @staticmethod
    def get_pci_slots():
        data = []
        context = pyudev.Context()
        for device in context.list_devices(subsystem='pci'):
            data.append(device.properties['PCI_SLOT_NAME'])
        return data

    @staticmethod
    def log_udev_event(action, device):
        print(action, device)
        # if action == 'add':
        #     print('USB INSERTEDDDDDDDDDDDDDDDDDDDDDDDDDD')
        #
        # elif action == 'remove':
        #
        #     print('USB EJECTEDDDDDDDDDDDDDDDDDDDDDDDDDD')
        #
        # elif action == 'change':
        #     print({**dict(device.items())})
        #     if 'DISK_MEDIA_CHANGE' in device:
        #         print(f'CD INSERTEDDDDDDDDDDDDDDDDDDDDDDDDDD {device.get("DISK_MEDIA_CHANGE")}')
        #     elif 'DISK_EJECT_REQUEST':
        #         print(f'CD EJECTEDDDDDDDDDDDDDDDDDDDDDDDDDD {device.get("DISK_EJECT_REQUEST")}')

    @staticmethod
    def mount_devices():
        context = pyudev.Context()
        for device in context.list_devices(subsystem='block'):
            if 'ID_FS_TYPE' in device:
                print('ID_FS_TYPE', device.get('ID_FS_TYPE'))
                print({**dict(device.items())})
                if device.get('DEVTYPE') == 'partition' and device.get(
                        'ID_BUS') == 'usb':
                    mountpoint = os.path.join('/mnt',
                                              device['DEVNAME'].lstrip('/'),
                                              str(device.get('ID_FS_LABEL')))
                    if not os.path.exists(mountpoint):
                        os.makedirs(mountpoint)
                    System.mount(device["DEVNAME"], mountpoint)
                elif 'ID_CDROM' in device and (device.get('ID_CDROM_MEDIA_STATE') or device.get('ID_CDROM_MEDIA_TRACK_COUNT')):
                    mountpoint = os.path.join(
                        '/mnt',
                        device['DEVNAME'].lstrip(
                            '/'),
                        str(
                            device.get(
                                'ID_FS_LABEL',
                                str(device.get('ID_MODEL'))
                            )
                        )
                    )
                    if not os.path.exists(mountpoint):
                        os.makedirs(mountpoint)
                    System.mount(device["DEVNAME"], mountpoint)

    @staticmethod
    def monitor_udev():
        print('Starting UDEV monitor...')
        logger.info('Starting UDEV monitor...')
        context = pyudev.Context()
        monitor = pyudev.Monitor.from_netlink(context)
        monitor.filter_by('block')
        if not os.path.exists('/mnt'):
            os.makedirs('/mnt')
            print('Created /mnt path')
        print('Started UDEV monitor. Polling ...')
        logger.info('Started UDEV monitor. Polling ...')

        for device in iter(monitor.poll, None):
            if 'ID_FS_TYPE' in device:
                print('ID_FS_TYPE', device.get('ID_FS_TYPE'))
                print({**dict(device.items())})
                if device.action == 'add' and device.get('.ID_FS_TYPE_NEW') and device.get('DEVTYPE') == 'partition':
                    print(f'Action "{device.action}" occured. Mounting {device["DEVNAME"]}.')
                    mountpoint = os.path.join('/mnt',
                                              device['DEVNAME'].lstrip('/'),
                                              str(device.get('ID_FS_LABEL')))
                    if not os.path.exists(mountpoint):
                        os.makedirs(mountpoint)
                    # AuditLog.objects.create(action='device_add',
                    #                           additional_data={"type": devtype, 'device_name': device["DEVNAME"]},
                    #                           description='device added')
                    logger.info({
                        'action': 'device_add',
                        'additional_data': dict(device.items())
                    })

                    System.mount(device["DEVNAME"], mountpoint)

                elif device.action == 'remove':
                    print(f'Action "{device.action}" occured. Unmounting {device["DEVNAME"]}')
                    # AuditLog.objects.create(action='device_remove',
                    #                           additional_data={"type": devtype, 'device_name': device["DEVNAME"]},
                    #                           description='device removed')
                    logger.info({
                        'action': 'device_remove',
                        'additional_data': dict(device.items())
                    })

                    result = System.unmount(device["DEVNAME"])
                    if result:
                        path = os.path.join('/mnt',
                                            device['DEVNAME'].lstrip('/'))
                        if os.path.exists(path):
                            shutil.rmtree(path)

                elif device.action == 'change':
                    print('*******************************CD-ROM STATE:', device.get('ID_CDROM_MEDIA_STATE'))
                    # AuditLog.objects.create(action='device_change',
                    #                           additional_data={"type": devtype, 'device_name': device["DEVNAME"]},
                    #                           description='device changed')
                    logger.info({
                        'action': 'device_change',
                        'additional_data': dict(device.items())
                    })

                    if 'DISK_MEDIA_CHANGE' in device and (device.get('ID_CDROM_MEDIA_STATE') or device.get('ID_CDROM_MEDIA_TRACK_COUNT')):
                        print(
                            f'Action "{device.action}" occured for DISK_MEDIA_CHANGE. Mounting {device["DEVNAME"]}')
                        mountpoint = os.path.join('/mnt',
                                                  device['DEVNAME'].lstrip(
                                                      '/'),
                                                  str(device.get(
                                                      'ID_FS_LABEL')))
                        if not os.path.exists(mountpoint):
                            os.makedirs(mountpoint)
                        System.mount(device["DEVNAME"], mountpoint)

                    elif 'DISK_EJECT_REQUEST' in device:
                        print(f'Action "{device.action}" occured for DISK_EJECT_REQUEST. Unmounting {device["DEVNAME"]}')
                        result = System.unmount(device["DEVNAME"])
                        if result:
                            path = os.path.join('/mnt',
                                                device['DEVNAME'].lstrip(
                                                    '/'))
                            if os.path.exists(path):
                                shutil.rmtree(path)

    @staticmethod
    def scan_from_email_process():
        from scans.email.imap import imap_process
        from scans.email.pop3 import pop3_process
        while True:
            try:
                system_settings = System.get_settings()
                email_protocol = system_settings.get('email_protocol')
                if email_protocol == 'IMAP':
                    imap_process()
                elif email_protocol == 'POP3':
                    pop3_process()
            except Exception as e:
                logger.info(str(e))
            time.sleep(5)

    @staticmethod
    def start_email_scanner():
        logger.info('Email scanner started.')
        email_settings = {}
        scanner = None
        login_failed = False
        conn_failed = True
        while True:
            logger.info('Checking the settings...')
            system_settings = System.get_settings()
            new_email_settings = {x: system_settings.get(x) for x in
                                  ['email_protocol', 'email_host',
                                   'email_incoming_port',
                                   'email_user', 'email_password']}
            protocol = new_email_settings['email_protocol']
            host = new_email_settings['email_host']
            port = new_email_settings['email_incoming_port']
            user = new_email_settings['email_user']
            password = System.decrypt_password(
                new_email_settings['email_password'])
            try:
                if new_email_settings == email_settings:
                    if conn_failed:
                        scanner.backend.login()
                        scanner.backend.fetch_messages()
                        login_failed = False
                        conn_failed = False
                    elif login_failed:
                        logger.info('Still failure.')

                    else:
                        scanner.backend.fetch_messages()
                else:
                    login_failed = False
                    conn_failed = True
                    email_settings = new_email_settings

                    scanner = EmailScanner(protocol, host, port, user,
                                           password)
                    scanner.backend.login()
                    scanner.backend.fetch_messages()
                    conn_failed = False

            except EmailProtocolError:
                login_failed = True
                conn_failed = False
                logger.info('Invalid protocol')

            except EmailAuthenticationError:
                login_failed = True
                conn_failed = False
                logger.info('Login failed.')
            except (ConnectionError, socket.gaierror):
                login_failed = False
                conn_failed = True
                logger.info('Connection failed.')

            time.sleep(5)

    @staticmethod
    def start_udev_observer():
        context = pyudev.Context()
        monitor = pyudev.Monitor.from_netlink(context)
        monitor.filter_by('block')
        observer = pyudev.MonitorObserver(monitor, System.log_udev_event)
        observer.start()

    @staticmethod
    def get_removable_disks(_filter=None):
        system_settings = System.get_settings()
        input_slots = system_settings['input_slots']
        output_slots = system_settings['output_slots']
        update_slots = system_settings['update_slots']
        context = pyudev.Context()
        psutil_partitions = psutil.disk_partitions()
        data = []
        for device in context.list_devices(subsystem='block', DEVTYPE='disk'):
            if not (device.attributes.asstring('removable') == '1' or dict(device.items()).get('ID_BUS') == 'usb'):
                continue

            id_path = device.get('ID_PATH')
            if _filter and (
                    (
                            _filter == 'input' and input_slots and id_path not in input_slots) or
                    (
                            _filter == 'output' and output_slots and id_path not in output_slots) or
                    (
                            _filter == 'update' and update_slots and id_path not in update_slots)
            ):
                continue

            mount_point = None
            for p in psutil_partitions:
                if p.device == device.device_node:
                    mount_point = p.mountpoint
                    break
            pci_slot = device.find_parent('pci').properties[
                'PCI_SLOT_NAME']
            item = {
                'device': {
                    'status': cache.get(device['DEVNAME']),
                    'PCI': pci_slot,
                    'MOUNT_POINT': mount_point,
                    'TOTAL_SIZE': shutil.disk_usage(
                        mount_point).total if mount_point else None,
                    **dict(device.items())
                },
                'partitions': []
            }

            for d in context.list_devices(subsystem='block',
                                          DEVTYPE='partition', parent=device):
                mount_point = None
                for p in psutil_partitions:
                    if p.device == d.device_node:
                        mount_point = p.mountpoint
                        break
                item['partitions'].append({
                    'status': cache.get(d['DEVNAME']),
                    'MOUNT_POINT': mount_point,
                    'TOTAL_SIZE': shutil.disk_usage(
                        mount_point).total if mount_point else None,
                    **dict(d.items())
                })

            data.append(item)

        return data

    @staticmethod
    def check_disk(devname):
        psutil_partitions = psutil.disk_partitions()
        for p in psutil_partitions:
            if p.device == devname and p.mountpoint:
                return True
        return False

    @staticmethod
    def walk_disk(path):
        items = []
        gen = os.walk(path)
        root, dirs, files = next(gen)
        for _dir in dirs:
            folder_size, files_count = System.get_folder_size(
                os.path.join(root, _dir))
            items.append({
                'hidden': _dir.startswith('.'),
                'name': _dir,
                'path': os.path.join(root, _dir),
                'type': 'dir',
                'size': folder_size,
                'files_count': files_count
            })

        for _file in files:
            items.append({
                'hidden': _file.startswith('.'),
                'name': _file,
                'path': os.path.join(root, _file),
                'type': 'file',
                'size': os.path.getsize(os.path.join(root, _file)),
            })

        return {
            'root': path,
            'items': items
        }

    @staticmethod
    def check_printer_settings(raise_exception=True):
        settings_ = System.get_settings()
        printer_ip = settings_['printer_ip']
        printer_port = settings_['printer_port']
        if not printer_ip or not printer_port:
            if raise_exception:
                raise PrinterError(_('Missing printer IP address and PORT'))
            return False, _('Missing printer IP address and PORT.')
        return printer_ip, printer_port

    @staticmethod
    def check_printer(raise_exception=True):
        printer_ip, printer_port = System.check_printer_settings(raise_exception=raise_exception)
        try:
            Printer(printer_ip, printer_port)
            return True, f'{printer_ip} responded on port {printer_port}'
        except:
            if raise_exception:
                raise PrinterError(
                    f'{printer_ip} did not respond on port {printer_port}')
            return False, f'{printer_ip} did not respond on port {printer_port}'

    @staticmethod
    def check_ftp():
        settings_ = System.get_settings()
        ftp_host = settings_['ftp_host']
        ftp_user = settings_['ftp_user']
        ftp_port = settings_['ftp_port']
        ftp_pass = System.decrypt_password(settings_['ftp_pass'])
        if not ftp_host or not ftp_port or not ftp_user or not ftp_pass:
            return False, _('Missing FTP host or port or username or password')

        ftp = FTP()
        try:
            ftp.connect(ftp_host, port=ftp_port, timeout=5)
            detail = ftp.login(ftp_user, ftp_pass)
            return True, detail
        except Exception as e:
            return False, str(e)
        finally:
            try:
                ftp.quit()
            except:
                pass

    @staticmethod
    def check_sftp():
        settings_ = System.get_settings()
        sftp_host = settings_['sftp_host']
        sftp_user = settings_['sftp_user']
        sftp_port = settings_['sftp_port']
        sftp_pass = System.decrypt_password(settings_['sftp_pass'])
        if not sftp_host or not sftp_port or not sftp_user or not sftp_pass:
            return False, _('Missing SFTP host or port or username or password')

        try:
            cnopts = pysftp.CnOpts()
            cnopts.hostkeys = None
            pysftp.Connection(host=sftp_host, port=sftp_port, username=sftp_user, password=sftp_pass, cnopts=cnopts)
            return True, 'Connection established successfully'
        except Exception as e:
            return False, str(e)

    @staticmethod
    def check_webdav():
        settings_ = System.get_settings()
        webdav_host = settings_['webdav_host']
        webdav_user = settings_['webdav_user']
        webdav_pass = System.decrypt_password(settings_['webdav_pass'])
        if not webdav_host or not webdav_user or not webdav_pass:
            return False, _('Missing WebDav host or port or username or password')
        try:
            options = {
                'webdav_hostname': f'{webdav_host}/{webdav_user}',
                'webdav_login': webdav_user,
                'webdav_password': webdav_pass,
            }
            client = Client(options)
            if not client.check():
                return False, 'Connection failed!'
            return True, 'Connection established successfully'
        except Exception as e:
            return False, str(e)

    @staticmethod
    def check_ldap():
        settings_ = System.get_settings()
        ldap_server_uri = settings_['ldap_server_uri']
        ldap_bind_dn = settings_['ldap_bind_dn']
        ldap_bind_password = System.decrypt_password(settings_['ldap_password'])
        try:
            connection = ldap.initialize(ldap_server_uri, bytes_mode=False)
            connection.simple_bind_s(ldap_bind_dn, ldap_bind_password)
            return True, 'Connection established successfully'
        except Exception as e:
            return False, str(e)

    @staticmethod
    def print_receipt(base64_file):
        printer_ip, printer_port = System.check_printer_settings()

        printer = Printer(printer_ip, printer_port)
        printer.print(base64_file)

        return True, None

    @staticmethod
    def generate_pdf_scan_result(date_time, total_count, infected_count,
                                 clean_count, av_names, infected_files):
        font_path = os.path.join(settings.STATIC_ROOT, 'scans', 'Vaziri.ttf')

        title_style = {
            'name': 'titleParph',
            'fontSize': 8,
            'leading': 20,
            'leftIndent': 0,
            'rightIndent': 0,
            'firstLineIndent': 0,
            'alignment': TA_CENTER,
            'spaceBefore': 0,
            'spaceAfter': 1
        }
        english_title_style = {
            'name': 'titleParphEn',
            'fontSize': 8,
            'leading': 20,
            'leftIndent': 0,
            'rightIndent': 0,
            'firstLineIndent': 0,
            'alignment': TA_LEFT,
            'spaceBefore': 0,
            'spaceAfter': 0
        }
        right_title_style = {
            'name': 'titleParphRight',
            'fontSize': 8,
            'leading': 20,
            'leftIndent': 0,
            'rightIndent': 0,
            'firstLineIndent': 0,
            'alignment': TA_RIGHT,
            'spaceBefore': 0,
            'spaceAfter': 1
        }

        if os.path.exists(font_path):
            font_name = 'Vaziri'
            try:
                pdfmetrics.registerFont(TTFont('Vaziri', font_path))
                title_style['fontName'] = font_name
                english_title_style['fontName'] = font_name
                right_title_style['fontName'] = font_name
            except:
                pass

        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(**title_style))
        styles.add(ParagraphStyle(**english_title_style))
        styles.add(ParagraphStyle(**right_title_style))

        data = [[
            Paragraph(get_display(arabic_reshaper.reshape(u'فایل های سالم')),
                      styles['titleParph']),
            Paragraph(get_display(arabic_reshaper.reshape(u'آلوده')),
                      styles['titleParph']),
            Paragraph(get_display(arabic_reshaper.reshape(u'کل فایل ها')),
                      styles['titleParph'])
        ],
            [
                Paragraph(get_display(arabic_reshaper.reshape(
                    str(clean_count))), styles['titleParph']),
                Paragraph(get_display(arabic_reshaper.reshape(
                    str(infected_count))), styles['titleParph']),
                Paragraph(get_display(arabic_reshaper.reshape(
                    str(total_count))), styles['titleParph'])
            ]]

        table = Table(data, 2 * [1 * inch], 2 * [0.25 * inch])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (2, 1), 'CENTER'),
            ('VALIGN', (0, 0), (2, 1), 'BOTTOM'),
            ('BOTTOMPADDING', (0, 0), (2, 1), -4),
            ('BACKGROUND', (0, 0), (2, 0), colors.gray),
            ('INNERGRID', (0, 0), (2, 1), 0.25, colors.black),
            ('BOX', (0, 0), (2, 1), 0.25, colors.black),
        ]))
        Story = []
        logo_path = os.path.join(settings.STATIC_ROOT, 'scans', 'logo.jpg')

        try:
            logo = System.get_settings()['logo']
            file_64_decode = base64.b64decode(logo)
            with open(logo_path, 'wb') as f:
                f.write(file_64_decode)
            image = Image(logo_path, 1.1 * inch, 1.1 * inch)
            Story.append(image)

        except:
            pass

        Story.append(
            Paragraph(get_display(arabic_reshaper.reshape(
                u'تاریخ : ' + str(date_time))),
                styles['titleParphRight'])
        )
        Story.append(table)
        # Story.append(Paragraph('<br/>', styles['titleParph']))
        Story.append(Spacer(10, 20))
        Story.append(Paragraph(get_display(
            arabic_reshaper.reshape(u'آنتی ویروس ها : ')),
            styles['titleParphRight']))
        Story.append(Paragraph(str(' // '.join(av_names.split(','))),
                               styles['titleParphEn']))
        # Story.append(Paragraph(get_display(
        #     arabic_reshaper.reshape(u'فایل های آلوده : ')),
        #     styles['titleParphRight']))
        Story.append(Paragraph(str(infected_files),
                               styles['titleParphEn']))

        pdf_file_path = os.path.join(settings.STATIC_ROOT, 'scans',
                                     'print_receipt.pdf')
        doc = SimpleDocTemplate(
            pdf_file_path,
            pagesize=(3.16 * inch, 8.27 * inch),
            rightMargin=10,
            leftMargin=10,
            topMargin=0,
            bottomMargin=5
        )
        doc.build(Story)

        try:
            with open(pdf_file_path, 'rb') as file:
                decoded_file = base64.b64encode(file.read())

        finally:
            if os.path.exists(pdf_file_path):
                os.remove(pdf_file_path)

            if os.path.exists(logo_path):
                os.remove(logo_path)

        return decoded_file.decode('utf-8')

    @staticmethod
    def walk_path_recursively(path):
        walk_list = []
        for (root, dirs, files) in os.walk(path, topdown=True):
            for file in files:
                walk_list.append(os.path.join(root, file))
        return walk_list

    @staticmethod
    def list_interfaces():
        def get_interface_status(interface):
            command = f"ifconfig -a | grep {interface} | " \
                      "awk -F '<' '{print $2}' | awk -F ',' '{print $1}'"
            result = execute_local(command)
            if result.exited == 0:
                output = result.stdout.strip()
                if output == 'UP':
                    return 'up'
                else:
                    return 'down'

        interface_addresses = psutil.net_if_addrs()
        interfaces = defaultdict(dict)
        for interface, addresses in interface_addresses.items():
            if interface == 'lo':
                continue

            interfaces[interface]['status'] = get_interface_status(interface)

            addrs = {}
            for address in addresses:
                addr = {}
                for field in address._fields:
                    if field not in ['family']:
                        addr[field] = getattr(address, field)

                        # fixing a bug
                        if isinstance(addr[field], str) and \
                                addr[field].endswith(f'%{interface}'):
                            addr[field] = addr[field].rstrip(f'%{interface}')

                addrs.setdefault(address.family.name, [])
                addrs[address.family.name].append(addr)

            interfaces[interface]['addresses'] = addrs

            interfaces[interface]['gateway4'] = None

        gateways = netifaces.gateways()
        for item in gateways.get(netifaces.AF_INET, []):
            gateway_address = item[0]
            interface_name = item[1]
            is_default = item[2]
            if is_default is True:
                interface = interfaces.get(interface_name)
                if interface:
                    interface['gateway4'] = gateway_address

        return interfaces

    @staticmethod
    def update_interfaces(content):
        # def change_interface_status(interface, status):
        #     command = f'ifconfig {interface} {status}'
        #     result = execute_local(command)
        #     return result.exited == 0

        def update_ubuntu_interfaces(content):
            netplan_files_paths = glob(f'{settings.INTERFACES_PATH}/*.yaml')
            netplan_docs = []
            for file_path in netplan_files_paths:
                with open(file_path) as file:
                    document = yaml.full_load(file)
                    netplan_docs.append(
                        {'doc': document, 'file_path': file_path})

            for name, info in content.items():
                af_inet = info['addresses'].get('AF_INET')
                if af_inet:
                    netmask = af_inet[0]['netmask']
                    netmask_bits = netmask_to_cidr(netmask)
                    ip = af_inet[0]['address']
                    address = f'{ip}/{netmask_bits}'
                    gateway = info.get('gateway4')
                    for doc in netplan_docs:
                        document = doc['doc']
                        ethernets = document['network'].get('ethernets', {})
                        bonds = document['network'].get('bonds', {})
                        for doc_int_name, doc_int_info in {**ethernets,
                                                           **bonds}.items():
                            if doc_int_name == name:
                                doc_int_info['addresses'] = [address]
                                if gateway:
                                    doc_int_info['gateway4'] = gateway
                                else:
                                    doc_int_info.pop('gateway4', None)

            for doc in netplan_docs:
                document = doc['doc']
                file_path = doc['file_path']
                with open(file_path, 'w+') as file:
                    yaml.dump(document, file)

            command = 'netplan generate && netplan apply'
            execute_local(command)
            time.sleep(5)

        update_ubuntu_interfaces(content)

        # for name, info in content.items():
        #     status = info['status']
        #     change_interface_status(name, status)

    @staticmethod
    def get_default_interface():
        interfaces = System.list_interfaces()
        for key, content in interfaces.items():
            if content['gateway4'] is not None:
                return {'interface': key, **interfaces[key]}

    @staticmethod
    def encrypt_password(password):
        key = base64.urlsafe_b64encode(bytes(settings.PRIVATE_KEY, 'utf8'))
        cipher_suite = Fernet(key)
        return cipher_suite.encrypt(bytes(password, 'utf8')).decode('utf8')

    @staticmethod
    def decrypt_password(encoded_password):
        try:
            key = base64.urlsafe_b64encode(bytes(settings.PRIVATE_KEY, 'utf8'))
            cipher_suite = Fernet(key)
            return cipher_suite.decrypt(bytes(encoded_password, 'utf8')).decode('utf8')
        except InvalidToken:
            return None
