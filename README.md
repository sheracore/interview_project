# interview_project
This project will be presented in interviews


# Viruspod Management Backend


## Installation

##### Update Ubuntu repositories
```bash
sudo apt update
```

##### Install base required packages from Ubuntu repositories
```bash
sudo apt install -y python3-venv nginx libvirt-dev
```

##### Install libs for building ldap and ssl-based application
```bash
sudo apt install -y build-essential python3-dev libsasl2-dev libldap2-dev libssl-dev
```

#### for python 3.8 in ubuntu 18.04
sudo apt install python3.8-dev

##### Install packages from Ubuntu repositories for Redis
```bash
sudo apt install -y redis-server
```

##### Install lib for building postgres db driver
```bash
sudo apt install -y libpq-dev postgresql postgresql-contrib
```

##### Install exfat-fuse exfat-utils for mounting exfat fs types in kiosk
```bash
sudo apt-get install exfat-fuse exfat-utils
```

##### For Postgres Database

Change values in brackets to what you set in .env file for db name, user and password.

```bash
sudo -u postgres psql
postgres=# CREATE DATABASE [your db name];
postgres=# CREATE USER [your db user] WITH PASSWORD [your db password];
postgres=# ALTER ROLE [your db user] SET client_encoding TO 'utf8';
postgres=# ALTER ROLE [your db user] SET default_transaction_isolation TO 'read committed';
postgres=# ALTER ROLE [your db user] SET timezone TO 'UTC';
postgres=# GRANT ALL PRIVILEGES ON DATABASE [your db name] TO [your db user];
postgres=# \q
```

##### Clone the repo from develop branch
```bash
git clone -b develop git@gitlab.fwutech.com:Multiscanner/viruspod-management-backend.git
```

##### Install Pip Packages
In project directory, create the venv, activate it and install the packages from given requirements text file as below:

if python version is 3.8 replace requirements38.txt instead of requirements.txt
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -r requirements.txt
```

#### If you want to install Pip packages offline
First on the system that has access to internet, download packages without installing them:
```bash
pip download -r requirements.txt
```

Then on the system that has no access to internet, install the downloaded packages:
```bash
pip install --no-index --find-links /path/to/download/dir/ -r requirements.txt
```

##### Configure .env file
In project directory, create and open .env file and configure following variables:

```bash
cd viruspod-management-backend
sudo nano .env
```

```text
DEBUG=True
SECRET_KEY=dasjklj90h[gf;vcdxcfgvhbnjuhyres  [Secret key must be at least 32 characters long]
I_AM_A_KIOSK= [True if you are deploying on a kiosk else False]
I_CAN_MANAGE_KIOSKS= [True if your are deploying the app to be central else False]
PUBLIC_SCAN=False [True if scan without login is needed]
URL_SCAN=False [True if internet is available for downloading file from url to scan]
ALLOWED_HOSTS=* #comma separated list of allowed ips to host the app or * to allow any
CORS_ORIGIN_WHITELIST= #comma separated list of allowed clients to access the app or * to allow any
CELERY_BROKER_URL=redis://localhost:6379 or amqp://localhost:5672
CELERY_TASK_DEFAULT_QUEUE=viruspod
DB_ENGINE=django.db.backends.postgresql_psycopg2 or django.db.backends.mysql
DB_NAME=[db name]
DB_USER=[db user]
DB_PASSWORD=[db password]
DB_HOST=localhost
DB_PORT=[empty] or 3306
MEDIA_ROOT=#defaults to /path/to/project/folder/media
SESSION_LIFETIME=600
JWT_ACCESS_TOKEN_LIFETIME=60
JWT_REFRESH_TOKEN_LIFETIME=600
INTERFACES_PATH=/etc/netplan

```

##### Notes on I_AM_A_KIOSK and I_CAN_MANAGE_KIOSKS env variables
Setting I_AM_A_KIOSK variable to True, results in enabling:
- Kiosk-specific endpoints: "shutdown", "restart", "unmount", "pci_slots", "check_printer", "check_ftp", "disks", "walk" and "check_disk"
- Kiosk-specific settings: "pincode", "printer and ftp settings" and "allowed removable disk pci slots"

Setting I_CAN_MANAGE_KIOSKS variable to True, results in enabling:
- Central-specific endpoints: "kiosks"

And disabling:
- Scan and scan related endpoints: "agents", "settings" and "mimetypes management"

##### Make DB migrations and static files collection

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createcachetable
python manage.py collectstatic --noinput
```

## Provision
To create default users and user groups run the following command.
```bash
python manage.py provision
```

To flush above data
```bash
python manage.py provision --flush
```

##### Change default plymouth theme
```bash
sudo update-alternatives --install /usr/share/plymouth/themes/default.plymouth default.plymouth /path/to/project/folder/static/core/splash/ubuntu-logo.plymouth 100
sudo update-alternatives --config default.plymouth
```

##### Configure GUNICORN Service

```text
[Unit]
Description=VIRUSPOD Gunicorn Daemon
After=network.target

[Service]
User=root
Group=www-data
WorkingDirectory=/path/to/project-folder
ExecStart=/path/to/project-folder/.venv/bin/gunicorn --config /path/to/project-folder/gunicorn.conf.py --bind unix:/path/to/temp/viruspod_mgm.sock proj.wsgi:application -w 5 --access-logfile /path/to/project-folder/gunicorn.log
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start the service

```bash
sudo systemctl enable viruspod-gunicorn
sudo service viruspod-gunicorn start
```

##### Configure CELERY Service

```text
[Unit]
Description=VIRUSPOD Celery Daemon
After=network.target

[Service]
User=root
Group=www-data
WorkingDirectory=/path/to/project-folder
ExecStart=/path/to/project-folder/.venv/bin/celery -A proj worker -l info --statedb=/path/to/worker.state
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start the service

```bash
sudo systemctl enable viruspod-celery.service
sudo service viruspod-celery start
```

##### Configure AGENTS STATUS Service (For MultiAV Mode)

Configure this service in multi av mode.

```bash
nano /etc/systemd/system/viruspod-agents-status.service
```

```text
[Unit]
Description=VIRUSPOD Agents status Daemon
After=network.target

[Service]                                                                      
User=root                                                                      
Group=www-data                                                                 
WorkingDirectory=/usr/local/viruspod-management-backend                        
ExecStart=/usr/local/viruspod-management-backend/.venv/bin/python manage.py agents
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start the service

```bash
sudo systemctl enable viruspod-agents-status.service
sudo service viruspod-agents-status start
```

##### Configure KIOSKS STATUS Service (For Central Mode)

Configure this service in central mode.

```bash
nano /etc/systemd/system/viruspod-kiosks-status.service
```

```text
[Unit]
Description=VIRUSPOD Kiosks status Daemon
After=network.target

[Service]                                                                      
User=root                                                                      
Group=www-data                                                                 
WorkingDirectory=/usr/local/viruspod-management-backend                        
ExecStart=/usr/local/viruspod-management-backend/.venv/bin/python manage.py kiosks
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start the service

```bash
sudo systemctl enable viruspod-kiosks-status.service
sudo service viruspod-kiosks-status start
```

##### Configure NGINX

```bash
nano /etc/nginx/conf.d/viruspod.conf
```

```text
server {
       listen 80;
       server_name vm_local_ip_address; # 192.168.123.61
       client_max_body_size 3000M;

       location = /favicon.ico {access_log off;log_not_found off;}

       location /static/ {
            root /path/to/project-folder;
       }

       location /media/ {
            root /path/to/project-folder/;
       }

       location / {
            client_max_body_size 3000M;
            include proxy_params;
            proxy_pass http://unix:/path/to/temp/viruspod_mgm.sock;
      }
}
```

Restart the nginx service
```bash
sudo service nginx restart
```

##### Configure UDEV Service (Optional)
If you want the backend to monitor and manage removable devices mount and unmount, use the following service

```bash
nano /etc/systemd/system/viruspod-udev.service
```

```text
[Unit]                                                                                                                                                                                                   
Description=VIRUSPOD UDEV Daemon                                                    
After=network.target                                                           
                                                                                
[Service]                                                                      
User=root                                                                      
Group=www-data                                                                 
WorkingDirectory=/usr/local/viruspod-management-backend                        
ExecStart=/usr/local/viruspod-management-backend/.venv/bin/python manage.py udev
Restart=always                                                                 
                                                                                
[Install]                                                                      
WantedBy=multi-user.target 
```

Enable and start the service

```bash
sudo systemctl enable viruspod-udev
sudo service viruspod-udev start
```

##### Configure Scan From Email Service (Optional)
If you want to give service to scan from email

```bash
nano /etc/systemd/system/viruspod-scan-from-email.service
```

```text
[Unit]                                                                                                                                                                                                   
Description=VIRUSPOD Scan From Email Daemon                                                    
After=network.target                                                           
                                                                                
[Service]                                                                      
User=root                                                                      
Group=www-data                                                                 
WorkingDirectory=/usr/local/viruspod-management-backend                        
ExecStart=/usr/local/viruspod-management-backend/.venv/bin/python manage.py scan_from_email
Restart=always                                                                 
                                                                                
[Install]                                                                      
WantedBy=multi-user.target 
```

Enable and start the service

```bash
sudo systemctl enable viruspod-scan-from-email
sudo systemctl start viruspod-scan-from-email
```

## Usage
Now you can browse API at:
```bash
http://[host]:[port]/swagger
```
