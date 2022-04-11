from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission

from core.models.system import System
from core.models.api import API


User = get_user_model()


class Command(BaseCommand):
    help = 'Provision super admin user, groups and settings'

    def create_default_groups(self):
        all_perms = Permission.objects.filter(content_type__app_label__in=[
            'agents',
            'core',
            'kiosks',
            'scans',
            'users'
        ])
        # pro = Group.objects.create(name='Pro')
        # pro.permissions.set(all_perms)
        view_group = Group.objects.create(name='View')
        view_group.permissions.set(
            all_perms.filter(codename__startswith='view'))

        add_group = Group.objects.create(name='Add')
        add_group.permissions.set(
            all_perms.filter(codename__startswith='add'))

        change_group = Group.objects.create(name='Change')
        change_group.permissions.set(
            all_perms.filter(codename__startswith='change'))

        delete_group = Group.objects.create(name='Delete')
        delete_group.permissions.set(
            all_perms.filter(codename__startswith='delete'))

        self.stdout.write(
            self.style.SUCCESS('View, Add, Change') + ' and ' +
            self.style.SUCCESS('Delete') + ' groups created.'
        )

    def create_users(self):
        instance = User.objects.create_superuser(username='admin',
                                                 password='admin')
        self.stdout.write(
            'Super user ' + self.style.SUCCESS('%s' % instance.username) +
            ' created.'
        )

    def add_arguments(self, parser):
        # Named (optional) arguments
        parser.add_argument(
            '--flush',
            action='store_true',
            help='Delete all provisioned items',
        )

    def handle(self, *args, **options):
        if options['flush']:
            num, data = User.objects.all().delete()
            self.stdout.write(
                self.style.SUCCESS('%s' % num) + ' users deleted.'
            )
            num, data = Group.objects.all().delete()
            self.stdout.write(
                self.style.SUCCESS('%s' % num) + ' user groups deleted.'
            )
            System.delete_settings()
            self.stdout.write(
                self.style.SUCCESS('Settings') + ' deleted.'
            )
            self.stdout.write('Finished flush successfully.')

        else:
            self.create_default_groups()
            self.create_users()
            API.objects.create(key='changeme', owner=User.objects.get(username='admin'))
            self.stdout.write('API key "changeme" created successfully. It is recommended to change it ASAP.')
            System.prepopulate_mimetypes()
            self.stdout.write('Mimetypes table populated successfully.')
            System.reset_settings()
            self.stdout.write('Settings cached successfully.')
            self.stdout.write('Finished provision successfully.')
