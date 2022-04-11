from django.core.management.base import BaseCommand

import socketserver
import logging
import threading

host = "0.0.0.0"

logger = logging.getLogger(__name__)
syslogger = logging.getLogger('syslog')


class Command(BaseCommand):
    help = 'Run a test syslog server'

    def add_arguments(self, parser):
        parser.add_argument('protocol', nargs=1, type=str)
        parser.add_argument('port', nargs=1, type=int)

    def handle(self, *args, **options):
        protocol = options['protocol'][0]
        port = options['port'][0]

        if protocol == 'udp':
            server = socketserver.UDPServer((host, port), SyslogUDPHandler)
            logger.info(f'Starting UDP syslog server on port {port}')
            server.serve_forever(poll_interval=0.5)
        elif protocol == 'tcp':
            tcp_server = socketserver.TCPServer((host, port), SyslogTCPHandler)
            tcp_thread = threading.Thread(target=tcp_server.serve_forever)
            logger.info(f'Starting TCP syslog server on port {port}')
            tcp_thread.start()


listening = False
# logging.basicConfig(level=logging.INFO, format='%(message)s',
#                     datefmt='', filename=LOG_FILE, filemode='a')


class SyslogUDPHandler(socketserver.BaseRequestHandler):

    def handle(self):
        data = bytes.decode(self.request[0].strip())
        data = data.replace("\x00", "\uFFFD")
        socket = self.request[1]
        msg = f'{self.client_address[0]}: {str(data)}'
        print(msg)
        syslogger.info(msg)


class SyslogTCPHandler(socketserver.BaseRequestHandler):
    End = '\n'

    def join_data(self, total_data):
        total_data = str(total_data)
        final_data = ''.join(total_data)
        for data in final_data.split(self.End):
            msg = f'{self.client_address[0]}: {str(data)}'
            print(msg)
            syslogger.info(msg)

    def handle(self):
        total_data = []
        data = self.request.recv(8192).strip()
        if self.End in str(data):
            split_index = data.rfind(self.End)
            total_data.append(data[:split_index])
            self.join_data(total_data)
            del total_data[:]
            total_data.append(data[split_index + 1:])
        else:
            total_data.append(data)
        if len(total_data) > 0:
            self.join_data(total_data)
