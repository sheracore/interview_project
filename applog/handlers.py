import logging
import socket
import random
import datetime
from logging import handlers as handlers, Handler
import threading

from django.utils import timezone

from core.utils.http import request as _request

logger = logging.getLogger(__name__)


class HTTPHandler(handlers.HTTPHandler):

    def __init__(self):
        super().__init__('', '')

    def _emit(self, record, url, method, headers):
        data = {
            'level': record.levelname,
            'message': record.msg,
        }
        if isinstance(record.msg, dict):
            data = record.msg
            data["level"] = record.levelname
            data['message'] = record.msg.get("action", '')

        try:
            _request(url, method,
                     headers=headers,
                     json=data,
                     timeout=10)
        except Exception:
            pass
            # self.handleError(record)

    def emit(self, record):
        from core.models.system import System
        app_settings = System.get_settings()
        log = app_settings.get('log')
        if not log:
            return

        http_url = app_settings.get('log_http_url')
        http_method = app_settings.get(
            'log_http_method')
        http_headers = app_settings.get(
            'log_http_headers')

        threading.Thread(target=self._emit, args=(record, http_url, http_method, http_headers)).start()


class SysLogHandler(handlers.SysLogHandler):

    def _emit(self, record, ip, port, protocol):
        socktypes = {
            'udp': socket.SOCK_DGRAM,
            'tcp': socket.SOCK_STREAM
        }

        try:
            super_handler = handlers.SysLogHandler(
                address=(ip, port), facility="auth",
                socktype=socktypes.get(protocol.lower()))
            return super_handler.emit(record)
        except Exception:
            pass
            # self.handleError(record)

    def emit(self, record):
        from core.models.system import System
        app_settings = System.get_settings()
        log = app_settings.get('syslog')
        if not log:
            return

        syslog_ip = app_settings.get('syslog_ip')
        syslog_port = app_settings.get('syslog_port')
        syslog_protocol = app_settings.get('syslog_protocol')

        self._emit(record, syslog_ip, syslog_port, syslog_protocol)

        # threading.Thread(target=self._emit, args=(record, syslog_ip, syslog_port, syslog_protocol)).start()


class ModelHandler(Handler):

    def __init__(self, model, expiry=0):
        super(ModelHandler, self).__init__()
        self.model = model
        self.expiry = int(expiry)

    def get_model(self):
        names = self.model.split('.')
        mod = __import__('.'.join(names[:-1]), fromlist=names[-1:])
        return getattr(mod, names[-1])

    def emit(self, record):
        # big try block here to exit silently if exception occurred
        # instantiate the model
        model = self.get_model()
        log_entry = model(level=record.levelname,
                          message=self.format(record))

        try:
            # test if msg is json and apply to log record object
            if isinstance(record.msg, dict):
                for key, value in record.msg.items():
                    if hasattr(log_entry, key):
                        setattr(log_entry, key, value)
            log_entry.save()

            # in 20% of time, check and delete expired logs
            if self.expiry and random.randint(1, 5) == 1:
                model.objects.filter(
                    created_at__lt=timezone.now() - datetime.timedelta(
                        seconds=self.expiry)).delete()
        except Exception:
            pass
            # self.handleError(record)


def test_log(message):
    handler = ModelHandler('core.models.AuditLog')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    logger.info(message)
    logger.removeHandler(handler)


def test_syslog(message):
    handler = SysLogHandler()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    logger.info(message)
    logger.removeHandler(handler)


def test_httphandler(message):
    handler = HTTPHandler()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    logger.info(message)
    logger.removeHandler(handler)
