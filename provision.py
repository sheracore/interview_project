from core.utils.commanding import execute_remote


def exec(host, command, user='fwutech', password='1qaz!QAZ', port=None):
    print(f'--------------------{command} Executation on {host}:'
          f'--------------------')
    execute_remote(host, command, user=user, password=password, port=port)


def deploy_viruspod(host='192.168.253.105', purge=False, user='viruspad',
               password='1qaz!QAZ', port=22):
    # exec(host, 'cd /usr/local/bin/dns-management-backend && '
    #            # 'sudo chown -R fwutech:fwutech . && '
    #            'sudo chmod -R 777 . && '
    #            'ls -al', user=user, password=password, port=port)
    exec(host,
         'cd /usr/local/viruspad/viruspod-management-backend && '
         'git reset --hard',
         user=user, password=password, port=port)
    exec(host,
         'cd /usr/local/viruspad/viruspod-management-backend && '
         'git pull',
         user=user, password=password, port=port)
    exec(host,
         'cd /usr/local/viruspad/viruspod-management-backend && '
         'source .venv/bin/activate && '
         'python manage.py makemigrations && '
         'python manage.py migrate && '
         'python manage.py createcachetable',
         user=user, password=password, port=port)

    if purge:
        exec(host,
             'sudo service viruspod-celery stop && '
             'cd /usr/local/viruspad/viruspod-management-backend && '
             'source .venv/bin/activate && '
             'celery -A proj purge -f && '
             'sudo service viruspod-celery start',
             user=user, password=password, port=port)

    else:
        exec(host,
             'sudo service viruspod-celery restart',
             user=user, password=password, port=port)

    restart_viruspod_services(host, user=user, password=password, port=port)


def restart_viruspod_services(host='192.168.253.105', user='viruspad', password='1qaz!QAZ',
                         port=22):
    # exec(host, 'sudo service rabbitmq-server restart',
    #      user=user, password=password, port=port)
    exec(host, 'sudo service viruspod-gunicorn restart',
         user=user, password=password, port=port)
    exec(host, 'sudo service viruspod-celery restart',
         user=user, password=password, port=port)


def deploy_kiosk(host, purge=False, user='fwutech',
               password='P@ssw0rd', port=50001):
    # exec(host, 'cd /usr/local/bin/dns-management-backend && '
    #            # 'sudo chown -R fwutech:fwutech . && '
    #            'sudo chmod -R 777 . && '
    #            'ls -al', user=user, password=password, port=port)
    exec(host,
         'cd /usr/local/viruspod-management-backend && '
         'git reset --hard',
         user=user, password=password, port=port)
    exec(host,
         'cd /usr/local/viruspod-management-backend && '
         'git pull',
         user=user, password=password, port=port)
    exec(host,
         'cd /usr/local/viruspod-management-backend && '
         'source .venv/bin/activate && '
         'python manage.py makemigrations && '
         'python manage.py migrate && '
         'python manage.py createcachetable',
         user=user, password=password, port=port)

    if purge:
        exec(host,
             'sudo service viruspod-celery stop && '
             'cd /usr/local/viruspod-management-backend && '
             'source .venv/bin/activate && '
             'celery -A proj purge -f && '
             'sudo service viruspod-celery start',
             user=user, password=password, port=port)

    else:
        exec(host,
             'sudo service viruspod-celery restart',
             user=user, password=password, port=port)

    restart_viruspod_services(host, user=user, password=password, port=port)


def deploy_viruspod_front(host='192.168.253.105', npm=False, user='viruspad',
                 password='1qaz!QAZ', port=22):
    exec(host,
         'cd /usr/local/viruspad/viruspod-management-front && '
         'sudo git reset --hard', user=user, password=password, port=port)
    exec(host,
         'cd /usr/local/viruspad/viruspod-management-front && '
         'sudo git pull', user=user, password=password, port=port)
    if npm:
        exec(host,
             'cd /usr/local/viruspad/viruspod-management-front && '
             'sudo npm install', user=user, password=password, port=port)
    exec(host,
         'cd /usr/local/viruspad/viruspod-management-front && '
         'sudo npm run build', user=user, password=password, port=port)
    exec(host,
         'sudo service nginx restart', user=user, password=password, port=port)


def deploy_kiosk_front(host, npm=False, user='fwutech',
                     password='P@ssw0rd', port=50001):
    exec(host,
         'cd /usr/local/viruspod-kiosk-frontend && '
         'sudo git reset --hard', user=user,
         password=password, port=port)
    exec(host,
         'cd /usr/local/viruspod-kiosk-frontend && '
         'sudo git pull', user=user,
         password=password, port=port)
    if npm:
        exec(host,
             'cd /usr/local/viruspod-kiosk-frontend && '
             'sudo npm install', user=user,
             password=password, port=port)
    exec(host,
         'cd /usr/local/viruspod-kiosk-frontend && '
         'sudo npm run build', user=user,
         password=password, port=port)

    exec(host,
         'sudo service nginx restart', user=user,
         password=password, port=port)


