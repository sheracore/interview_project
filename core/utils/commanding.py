from invoke import Responder, run
from fabric import Connection
from fabric.transfer import Transfer


def execute_local(command):
    result = run(command, warn=True)
    return result


def create_connection(host, user, password, port=None):
    return Connection(host, user, connect_kwargs={'password': password}, port=port)


def execute_remote(host, command, user=None, password=None, port=None):
    c = create_connection(host, user, password, port=port)
    sudopass = Responder(pattern=fr'\[sudo\] password for {user}:',
                         response=f'{password}\n')
    result = c.run(command, pty=True, watchers=[sudopass])
    c.close()
    return result


def transfer(origin, dest, host, user, password):
    c = create_connection(host, user, password)
    t = Transfer(c)
    result = t.put(origin, remote=dest)
    print("Uploaded {0.local} to {0.remote} ({1})".format(result, host))