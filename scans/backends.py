import json
import time
import os
import importlib
import libvirt
import rpyc
from django.conf import settings
from django.core.files import File as DjangoFile
from celery import group
from celery.result import GroupResult
import redis

from core.mixins import AsyncMixin
from scans.models.file import File
from scans.tasks import scan_path, save_results

import logging
logger = logging.getLogger(__name__)

SCAN_QUEUE_NAME = 'scan-sessions'
redis_conn = redis.Redis()

class Session:
    def __init__(self, _id, start_time=None, name=None):
        self.id = _id
        self.name = name if name else f'Session-{_id}'
        self.start_time = start_time
        self.result = GroupResult.restore(self.id)
        self.state = 'PENDING'

    @staticmethod
    def queue_messages(queue=SCAN_QUEUE_NAME):
        messages = redis_conn.lrange(queue, 0, redis_conn.llen(queue))
        return messages

    @staticmethod
    def active_groups(queue=SCAN_QUEUE_NAME):
        messages = redis_conn.lrange(queue, 0, redis_conn.llen(queue))
        waiting_groups = set()
        for msg in messages:
            decoded = json.loads(msg.decode('utf-8'))
            waiting_groups.add(
                (
                    decoded['headers']['group'],
                    decoded['properties']['time'],
                )
            )
        return waiting_groups

    @classmethod
    def active_sessions(cls):
        sessions = []
        for waiting_group in cls.active_groups():
            sessions.append(
                cls(waiting_group[0], start_time=waiting_group[1]),
            )
        return sessions

    def waiting_sessions(self):
        return list(filter(lambda session: session.start_time < self.start_time, self.active_sessions()))

    def get_start_time(self):
        if self.start_time:
            return self.start_time
        else:
            messages = self.queue_messages()
            if not messages:
                return None
            for task in messages:
                value = json.loads(task.decode('utf-8'))
                group_id = value.get('headers').get('group')
                if group_id == self.id:
                    return value.get('properties').get('time')

    def waiting_tasks(self):
        results = self.queue_messages()
        if not results:
            return []

        current_group_time = self.get_start_time()
        tasks = list()
        for task in results:
            value = json.loads(task.decode('utf-8'))
            group_time = value.get('properties').get('time')
            if group_time < current_group_time:
                tasks.append(value)

        return tasks

    def progress(self, detail=False):
        current = self.result
        results = []
        progresses = []
        while current:
            total_children = 0
            total_done = 0
            for child in current.children:
                total_children += 1
                if child.state in {'SUCCESS', 'FAILURE', 'REVOKED'}:
                    total_done += 1
                if detail:
                    results.append({
                        'state': child.state,
                        'result': child.result
                    })
            progresses.append(total_done / total_children)
            current = current.parent

        if self.state == 'REVOKED':
            percent = 100
        elif not progresses:
            percent = 0
        else:
            percent = sum(progresses) * 100 / len(progresses)

        if detail:
            return {
                'waiting_sessions': len(self.waiting_sessions()),
                'waiting_tasks': len(self.waiting_tasks()),
                'percent': percent,
                'results': results
            }
        else:
            return {
                'waiting_sessions': len(self.waiting_sessions()),
                'waiting_tasks': len(self.waiting_tasks()),
                'percent': percent
            }

    def total_count(self):
        return len(self.progress(detail=True)['results'])

    def revoked_count(self):
        return len(
            list(
                filter(
                    lambda result: result['state'] == 'REVOKED',
                    self.progress(detail=True)['results']
                )
            )
        )

    def cancel(self):
        if self.result:
            self.result.revoke(terminate=True)
            self.state = 'REVOKED'


class Scanner:
    def __init__(self, av_name, host, port):
        self.av_name = av_name
        self.host = host
        self.port = port

    def get_av_class(self):
        module = importlib.import_module(f'agents.backends.{self.av_name}')
        backend = getattr(module, f'{self.av_name.capitalize()}Backend')
        return backend

    def get_av(self):
        backend = self.get_av_class()
        return backend(self.host)

    @property
    def av(self):
        return self.get_av()

    def ping(self):
        with rpyc.classic.connect(self.host, self.port):
            return True


class LibVirtScannerBackend:
    def __init__(self):
        self.conn = libvirt.open("qemu:///system")

    def active_scanners(self):
        domains = self.conn.listAllDomains()
        scanners = [
            Scanner(domain.name, domain.ip, 18811) for domain in domains
        ]
        return scanners

    def get_scanner(self, av_name):
        domain = self.conn.lookupByName(av_name)
        return Scanner(domain.name, domain.ip, 18811)


class ModelScannerBackend:
    from agents.models import Agent
    model = Agent

    def active_scanners(self):
        scanners = []
        for agent in self.model.objects.filter(active=True):
            scanners.append(
                Scanner(agent.av_name, agent.api_ip, 18811)
            )
        return scanners

    def get_scanner(self, av_name):
        agent = self.model.objects.get(av_name=av_name)
        return Scanner(agent.av_name, agent.api_ip, 18811)


class MultiScanner(AsyncMixin):
    def __init__(self, paths, scanners):
        self.paths = paths
        self.scanners = scanners

    def compose_tasks(self, paths):
        # composed = group()
        groups = []
        for path in paths:
            if isinstance(path, list):
                groups.append(self.compose_tasks(path))
            else:
                groups.append(group(
                    scan_path.s(path, scanner.av_name, scanner.host).set(queue=SCAN_QUEUE_NAME)
                    for scanner in self.scanners
                ))
        return group(*groups) | save_results.s().set(queue=settings.CELERY_TASK_DEFAULT_QUEUE)

    def scan(self):
        start_time = time.time()
        composed = self.compose_tasks(self.paths)
        result = composed.apply_async(
            time=start_time,
            count=len(self.paths)
        )
        group_result = result.parent
        group_result.save()
        return Session(group_result.id, start_time)


def scan_on_agents(files_num=1):
    scanners = ModelScannerBackend().active_scanners()

    paths = []
    for i in range(files_num):
        with open(os.path.join(settings.MEDIA_ROOT,
                               f'test_multi_agent_file_{i}.txt'), 'w') as f:
            f.write(
                'X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*')
            paths.append(f.name)

    multi_scanner = MultiScanner(paths, scanners)
    return multi_scanner.scan()


def test_tasks(files_num=1, paths=None):
    scanners = [
        Scanner('eset', '1.1.1.1', 18811),
        Scanner('adaware', '1.1.1.2', 18811),
        # Scanner('kaspersky', '1.1.1.3', 18811),
        # Scanner('avg', '1.1.1.4', 18811),
        # Scanner('avira', '1.1.1.5', 18811)
    ]

    if not paths:
        paths = []
        for i in range(files_num):
            with open(os.path.join(settings.MEDIA_ROOT,
                                   f'test_multi_agent_file_{i}.txt'),
                      'w') as f:
                f.write(
                    'X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*')
                paths.append(f.name)

    multi_scanner = MultiScanner(paths, scanners)
    return multi_scanner.scan()


def test_concurrency(num):
    from time import sleep
    sessions = []
    for i in range(0, num):
        a = test_tasks(10)
        sessions.append(a)
        sleep(1)

    total_progress = 0
    while total_progress < 100:
        total_progress = 0
        counter = 0
        logger.info('*************************************************************************************************')
        for session in sessions:
            counter += 1
            progress = session.progress()
            waiting_sessions = progress['waiting_sessions']
            waiting_tasks = progress['waiting_tasks']
            percent = progress['percent']
            logger.info(f'{counter} - {session.id}'
                        f' - waiting_tasks:{waiting_tasks}'
                        f' - waiting_sessions:{waiting_sessions}'
                        f' - percent: {percent}')
            total_progress += percent
        total_progress = total_progress/len(sessions)
        sleep(3)


def realtime_test(num=1):
    from time import sleep
    session = test_tasks(num)
    print(session.id)
    counter = 0
    while session.progress() < 100:
        counter += 1
        print(session.progress())
        print(session.revoked_count())
        sleep(1)
        if counter == 10:
            session.cancel()
            print('session canceled')
    return session


def test_agents():
    with open(os.path.join(settings.MEDIA_ROOT, 'test_file.txt'), 'w') as f:
        f.write(
            'X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*')
        path = f.name
    scanners = ModelScannerBackend().active_scanners()
    tasks = group(
        scan_path.si(path, scanner.av_name, scanner.host)
        for scanner in scanners
    )
    return AsyncMixin.perform_async(tasks, on_commit=False)


def test_scan_concurrency(av_name, concurrent=1):
    scanner = ModelScannerBackend().get_scanner(av_name)
    paths = []
    for i in range(concurrent):
        with open(os.path.join(settings.MEDIA_ROOT, f'test_file_{i}.txt'),
                  'w') as f:
            f.write(
                'X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*')
            paths.append(f.name)
    tasks = group(
        scan_path.si(path, scanner.av_name, scanner.host)
        for path in paths
    )
    return AsyncMixin.perform_async(tasks, on_commit=False)


class FileScanBackend(AsyncMixin):
    scanner_backend_class = ModelScannerBackend
    validators = []

    def __init__(self, files=None):
        self._files = files or []
        self.instances = None

    def get_files(self):
        return self._files

    def get_scanner_backend_class(self, *args, **kwargs):
        return self.scanner_backend_class

    def get_scanner_backend(self, *args, **kwargs):
        return self.get_scanner_backend_class(*args, **kwargs)()

    def get_scanners(self, *args, **kwargs):
        return self.get_scanner_backend(*args, **kwargs).active_scanners()

    def create_file(self, file):
        file = DjangoFile(file)
        file.name = os.path.split(file.name)[-1]
        return file

    def create(self):
        # session = Session.objects.create()
        instances = []
        for file in self.get_files():
            instances.append(
                # File(file=self.create_file(file), session=session)
                File(file=self.create_file(file))
            )
        self.instances = File.objects.bulk_create(instances)

    def scan(self):
        self.create()
        multi_scanner = MultiScanner(
            [instance.file.path for instance in self.instances],
            self.get_scanners())

        multi_scanner.scan()
        self.multi_scanner = multi_scanner
        return self.multi_scanner


class DiskScanBackend(FileScanBackend):

    def __init__(self, paths=None):
        super().__init__()
        self._paths = paths

    def get_files(self):
        files = []
