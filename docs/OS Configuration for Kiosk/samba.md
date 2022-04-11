# Samba Installation
## Server Side
### Install Samba following below commands
```bash
sudo apt install samba
```
### make a directory for samba
```bash
sudo mkdir /smb
```
### add below script to end of line in (smb.conf)

```bash
sudo nano /etc/samba/smb.conf
```
```editorconfig
[smb]
comment = Samba on Kiosk
path = /smb
read only = yes
browsable = yes

```
### Then restart smbd.service
```bash
sudo service smbd restart
```
### Add user for samba (Username and Password will be use in .smbcreds on User Side)
```bash
sudo smbpasswd -a fwutech
```
### Add below script to fstab
```bash
sudo nano /etc/fstab
```
```editorconfig
tmpfs /smb tmpfs size=6G,defaults,noexec,nosuid 0 0
```
```bash
sudo reboot
```
## Machine Side
### Install below package
```bash
sudo apt install cifs-utils
```
### Make samba Directory
```bash
sudo mkdir /smb
```
### Then make .smbcreds in /smb (Username and Password are same in Server Side)
```bash
sudo nano /smb/.smbcreds
```
```editorconfig
Username=fwutech
Password=P@ssw0rd
```
### Add below script in fstab
```bash
sudo nano /etc/fstab
```
```editorconfig
//192.168.100.1/smb /smb cifs  credentials=/smb/.smbcreds,defaults 0 0
```
```bash
sudo reboot
```