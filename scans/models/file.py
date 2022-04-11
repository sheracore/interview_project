import os
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.db import transaction

from core.models.mixins import DateMixin, UpdateModelMixin
from core.models.system import System
from core.mixins import AsyncMixin
from scans.tasks import extract_file, scan_file, \
    set_file_info, bulk_create_from_disk, \
    create_from_url, create_from_path
from scans.exceptions import InvalidPostScanOperation
from scans.models.session import Session
from core.fields import SafeCharField
from core.utils.files import is_archive_file

User = get_user_model()


class AbstractFileInfo(models.Model):
    size = models.FloatField(null=True)
    md5 = models.CharField(max_length=256)
    sha1 = models.CharField(max_length=256)
    sha256 = models.CharField(max_length=256)
    ext_match = models.BooleanField(null=True)
    extension = models.CharField(max_length=256)
    mimetype = models.CharField(max_length=256)

    class Meta:
        abstract = True


class FileInfo(AbstractFileInfo, DateMixin, UpdateModelMixin):
    size = models.FloatField(null=True)
    md5 = models.CharField(max_length=256)
    sha1 = models.CharField(max_length=256)
    sha256 = models.CharField(max_length=256)
    ext_match = models.BooleanField(null=True)
    extension = models.CharField(max_length=256)
    mimetype = models.CharField(max_length=256)

    class Meta:
        default_permissions = []


def get_file_upload_path(instance, filename):
    if instance.user:
        folder_name = instance.user.username
    else:
        folder_name = 'public'
    return os.path.join("files/%s" % folder_name, filename)


class FileQuerySet(models.QuerySet):
    pass


class FileManager(models.Manager, AsyncMixin):

    def get_queryset(self):
        return FileQuerySet(self.model, using=self._db)

    def cleanup_disk(self, days_older_than):
        qs = self.get_queryset()
        older_files = qs.filter(
            created_at__lt=timezone.now() - timedelta(days=days_older_than),
            deleted=False)

        for instance in older_files:
            instance.file.delete(save=False)
            self.model.objects.filter(pk=instance.pk).update(deleted=True)

        return older_files.count()

    def bulk_create_from_disk(self, paths, scan=False, extract=False,
                              agents=None, owner=None, _async=True):
        if agents:
            agent_pks = [agent.pk for agent in agents]
        else:
            agent_pks = None

        owner_id = owner.pk if owner else None
        session = Session.objects.create(source='disk')

        if _async:
            self.perform_async(
                bulk_create_from_disk.si(session.pk, paths, scan=scan,
                                         extract=extract,
                                         agent_pks=agent_pks,
                                         owner_id=owner_id),
                session_id=session.pk
            )
            return session
            # app.control.add_consumer(queue=session_id, reply=True)
        else:
            return bulk_create_from_disk(session.pk, paths, scan=scan,
                                         extract=extract,
                                         agent_pks=agent_pks,
                                         owner_id=owner_id)

    def create_from_url(self, url, save_as=None, scan=False, extract=False,
                        agents=None, owner=None, _async=True):
        if agents:
            agent_pks = [agent.pk for agent in agents]
        else:
            agent_pks = None

        owner_id = owner.pk if owner else None

        session = Session.objects.create(source='url')

        if _async:
            self.perform_async(
                create_from_url.si(session.pk, url, save_as=save_as, scan=scan,
                                   extract=extract,
                                   agent_pks=agent_pks, owner_id=owner_id),
                session_id=session.pk
            )
            # app.control.add_consumer(queue=session_id, reply=True)
            return session
        else:
            return create_from_url(session.pk, url, save_as=save_as, scan=scan,
                                   extract=extract,
                                   agent_pks=agent_pks, owner_id=owner_id)

    def create_from_path(self, path, scan=False, extract=False, agents=None,
                         owner=None, _async=False):
        if agents:
            agent_pks = [agent.pk for agent in agents]
        else:
            agent_pks = None

        owner_id = owner.pk if owner else None
        session = Session.objects.create(source='upload')

        if _async:
            self.perform_async(
                create_from_path.si(session.pk, path, scan=scan,
                                    extract=extract,
                                    agent_pks=agent_pks, owner_id=owner_id),
                session_id=session.pk
            )
            # app.control.add_consumer(queue=session_id, reply=True)
            return session
        else:
            return create_from_path(path, scan=scan, extract=extract,
                                    agent_pks=agent_pks, owner_id=owner_id)


class AbstractFile(models.Model):
    username = models.CharField(max_length=32, null=True)
    display_name = models.CharField(max_length=256)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=64, blank=True)
    valid = models.BooleanField(default=False)
    # whether the source file is deleted on disk in media root
    deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True


class BaseFile(AbstractFile, DateMixin):
    class Meta:
        abstract = True


class File(BaseFile, UpdateModelMixin, AsyncMixin):
    file = models.FileField(max_length=1024, upload_to=get_file_upload_path,
                            null=True)
    info = models.ForeignKey(FileInfo, related_name='files',
                             on_delete=models.CASCADE, null=True,
                             editable=False)
    session = models.ForeignKey(Session, related_name='files',
                                on_delete=models.CASCADE, editable=False)
    user = models.ForeignKey(User, related_name='files',
                             on_delete=models.SET_NULL, null=True,
                             editable=False)

    # for next cloud. it is just for test phase only.
    client_username = SafeCharField(max_length=128, blank=True, null=True)
    client_file_name = SafeCharField(max_length=256, blank=True, null=True)

    # archive file id which this file belongs to
    parent = models.ForeignKey('File', related_name='children',
                               editable=False, null=True,
                               on_delete=models.CASCADE)
    progress = models.FloatField(null=True, db_index=True, editable=False)
    infected = models.BooleanField(null=True, db_index=True, editable=False)

    objects = FileManager()

    class Meta:
        verbose_name = _('File')
        verbose_name_plural = _('Files')
        # unique_together = ('file', 'session')
        permissions = [
            ('cleanup', 'Can cleanup storage disk'),
            ('delete_files', 'Can delete multiple Files with session ID')
        ]

    def __str__(self):
        return '%s' % self.file

    def set_file_info(self, _async=True):
        if _async:
            self.perform_async(
                set_file_info.si(self.pk),
                session_id=self.session.pk
            )
        else:
            return set_file_info(self.pk)

    def extract(self, _async=True):
        if not is_archive_file(self.file.path):
            return False

        children = self.children.all()

        if children.exists():
            return False

        if _async:
            self.perform_async(
                extract_file.si(self.pk),
                session_id=self.session.pk
            )
        else:
            return extract_file(self.pk)

    def scan(self, _async=True, extract=False, agents=None):
        agent_pks = agents and [agent.pk for agent in agents]
        if _async:
            self.perform_async(
                scan_file.si(self.pk, _async=_async, extract=extract,
                             agent_pks=agent_pks),
                session_id=self.session.pk
            )
        else:
            return scan_file(self.pk, _async=_async, extract=extract,
                             agent_pks=agent_pks)

    def eval_infected(self, clean_acceptance_index, valid_acceptance_index):
        total_scans = self.scans.count()
        if total_scans:
            if self.scans.filter(
                    status_code=None).exists() or self.scans.filter(
                infected_num__isnull=True).count() >= (
                    1 - valid_acceptance_index) * total_scans:
                return None
            elif self.scans.filter(infected_num__gt=0).count() >= (
                    1 - clean_acceptance_index) * total_scans:
                return True
            else:
                return False
        else:
            return None

    def update_scan_state(self):
        _settings = System.get_settings()
        clean_acceptance_index = _settings['clean_acceptance_index']
        valid_acceptance_index = _settings['valid_acceptance_index']
        with transaction.atomic():
            obj = File.objects.select_for_update().filter(pk=self.pk).get()
            if obj.children.exists():
                total_children = obj.children.filter(valid=True).count(
                )
                total_children_scanned = obj.children.filter(
                    progress=100).count()
                obj.progress = round(100 * total_children_scanned / total_children, 1)

                for child in obj.children.all():
                    infected = child.eval_infected(clean_acceptance_index,
                                                   valid_acceptance_index)
                    if infected or infected is None:
                        obj.infected = infected
                        break
                    else:
                        obj.infected = False
            else:
                total_scans = obj.scans.count()
                if total_scans:
                    obj.progress = round(100 * obj.scans.exclude(
                        status_code=None).count() / total_scans, 1)

                    if obj.scans.filter(status_code=None).exists():
                        obj.infected = None
                    elif obj.scans.filter(
                            infected_num__isnull=True).count() >= (
                            1 - valid_acceptance_index) * total_scans:
                        obj.infected = None
                    elif obj.scans.filter(infected_num__gt=0).count() >= (
                            1 - clean_acceptance_index) * total_scans:
                        obj.infected = True
                    else:
                        obj.infected = False

                else:
                    obj.infected = None
            obj.save()

    def postscan_valid(self, raise_exception=True):
        is_valid = self.progress == 100 and self.infected is False
        if is_valid:
            return True
        elif raise_exception:
            raise InvalidPostScanOperation(
                'Scan is not yet complete or the file is infected')
        else:
            return False


@receiver(post_delete, sender=File)
def post_delete_file(sender, instance, *args, **kwargs):
    instance.file.delete(save=False)


# @receiver(post_save, sender=File)
# def update_parent_file_state(sender, instance, created, *args, **kwargs):
#     try:
#         parent = File.objects.get(session=instance.session,
#                                   file=instance.parent)
#         parent.update_scan_state()
#     except ObjectDoesNotExist:
#         pass
#
#     instance.session.update_progress()
