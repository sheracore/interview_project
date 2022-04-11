import os


from django.conf import settings


def register_existing_files(media_root=None):
    from scans.models.file import File

    media_root = media_root or settings.MEDIA_ROOT
    gen = os.walk(media_root)
    for i in gen:
        for file in i[2]:
            file_path = i[0].rstrip('/') + '/' + file
            print(f'Inserting {file_path}')
            try:
                File.objects.create_from_path(path=file_path, extract=True)
            except:
                continue
