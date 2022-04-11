import pyudev
import psutil
import uuid
import io
from PIL import Image
import magic
import mimetypes
import os
import hashlib
import requests
import tempfile
import tarfile
import gzip
import zipfile
import rarfile
import py7zr
import base64

from django.core import files
from django.core.files import File
from django.utils.text import slugify


def generate_photo_file(name='test', format='png'):
    file = io.BytesIO()
    image = Image.new('RGBA', size=(100, 100), color=(155, 0, 0))
    image.save(file, format)
    file.name = f'{name}.{format}'
    file.seek(0)
    return file


def generate_file(content='', name='test_file.txt'):
    with open(name, 'w') as file:
        django_file = File(file)
        django_file.write(content)
        django_file.seek(0)

    return django_file


def index_dir(path):
    files = []
    import os
    gen = os.walk(path)
    for i in gen:
        for file in i[2]:
            file_path = i[0].rstrip('/') + '/' + file
            print(file_path)
            files.append(file_path)
        for folder in i[1]:
            index_dir(i[0].rstrip('/')+'/'+folder)
    return files


def discover_mimetype(file):
    chunk = file.read(8192)
    mime_type = magic.from_buffer(chunk, mime=True)
    return mime_type or 'generic-data'


def discover_file_info(file):
    """
        Generate checksums of the given file
    """
    chunk = file.read(8192)

    sh1 = hashlib.sha1()
    sha256 = hashlib.sha256()
    md5 = hashlib.md5()

    while chunk:
        sh1.update(chunk)
        sha256.update(chunk)
        md5.update(chunk)
        chunk = file.read(8192)

    sh1 = sh1.hexdigest()
    sha256 = sha256.hexdigest()
    md5 = md5.hexdigest()

    data = {
        'sha1': sh1,
        'sha256': sha256,
        'md5': md5
    }
    return data


def download_file(url, save_as=None):
    response = requests.get(url, stream=True, allow_redirects=True)
    temp_file = tempfile.NamedTemporaryFile()

    for chunk in response.iter_content(2000):
        if not chunk:
            break

        temp_file.write(chunk)

    temp_file.flush()

    if save_as:
        filename = save_as
    else:
        filename = slugify(url)

    return files.File(temp_file, name=filename)


def validate_download_size(url):

    """
    Validate URL file size

    """
    from core.models import System

    try:
        response = requests.head(url, allow_redirects=True)
    except requests.exceptions.RequestException:
        return False, 'There was an error downloading file.'

    max_file_size = System.get_settings()['max_file_size']
    if max_file_size:
        if int(response.headers.get('content-length', 0)) > max_file_size:
            return False

    return True


def is_archive_file(file_path):
    if tarfile.is_tarfile(file_path) or\
            zipfile.is_zipfile(file_path) or\
            rarfile.is_rarfile(file_path) or\
            py7zr.is_7zfile(file_path):
        return True
    else:
        return False


def extract_compressed_file_recursively(file_path, delete_file=False, raise_exception=True):

    extract_root_path, filename = os.path.split(file_path)
    extract_folder_path = os.path.join(extract_root_path,
                                       '.'.join(
                                           ['tmp', filename, str(uuid.uuid4())]))

    if tarfile.is_tarfile(file_path):

        tar = tarfile.open(file_path)
        tar.extractall(extract_folder_path)
        tar.close()

    elif zipfile.is_zipfile(file_path):
        with zipfile.ZipFile(file_path) as f:
            f.extractall(extract_folder_path)

    elif rarfile.is_rarfile(file_path):
        with rarfile.RarFile(file_path) as f:
            f.extractall(extract_folder_path)

    elif py7zr.is_7zfile(file_path):
        with py7zr.SevenZipFile(file_path) as f:
            f.extractall(extract_folder_path)

    else:
        if raise_exception:
            raise Exception('Could not detect the archive type')

    gen = os.walk(extract_folder_path)
    for i in gen:
        for file in i[2]:
            nested_file_path = i[0].rstrip('/') + '/' + file
            if is_archive_file(nested_file_path):
                extract_compressed_file_recursively(nested_file_path,
                                                    delete_file=True)

    if delete_file:
        os.remove(file_path)
    return extract_folder_path


def extract_compressed_file(file_path, delete_file=False, raise_exception=True,
                            dst=None, recursive=False):
    if dst:
        extract_folder_path = dst
    else:
        extract_root_path, filename = os.path.split(file_path)
        extract_folder_path = os.path.join(extract_root_path,
                                           '.'.join(
                                               ['tmp', filename,
                                                str(uuid.uuid4())]))

    if tarfile.is_tarfile(file_path):

        tar = tarfile.open(file_path)
        tar.extractall(extract_folder_path)
        tar.close()

    elif zipfile.is_zipfile(file_path):
        with zipfile.ZipFile(file_path) as f:
            f.extractall(extract_folder_path)

    elif rarfile.is_rarfile(file_path):
        with rarfile.RarFile(file_path) as f:
            f.extractall(extract_folder_path)

    elif py7zr.is_7zfile(file_path):
        with py7zr.SevenZipFile(file_path) as f:
            f.extractall(extract_folder_path)

    else:
        if raise_exception:
            raise Exception('Could not detect the archive type')
    if recursive:
        gen = os.walk(extract_folder_path)
        for i in gen:
            for file in i[2]:
                nested_file_path = i[0].rstrip('/') + '/' + file
                if is_archive_file(nested_file_path):
                    extract_compressed_file(nested_file_path,
                                            recursive=recursive,
                                            delete_file=True)

    if delete_file:
        os.remove(file_path)
    return extract_folder_path.rstrip()


def get_mounts():

    context = pyudev.Context()

    removable = [device for device in
                 context.list_devices(subsystem='block', DEVTYPE='disk') if
                 device.attributes.asstring('removable') == "1"]
    data = []
    for device in removable:
        partitions = [device.device_node for device in
                      context.list_devices(subsystem='block',
                                           DEVTYPE='partition',
                                           parent=device)]
        for p in psutil.disk_partitions():
            if p.device in partitions:
                data.append({
                    'device': p.device,
                    'mountpoint': p.mountpoint
                })

    return data
