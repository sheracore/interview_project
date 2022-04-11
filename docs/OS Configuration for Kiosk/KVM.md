# KVM Installation and Configuration
##Install QEMU KVM Packages
```bash
sudo apt install qemu
sudo apt install qemu-kvm 
sudo apt install virtinst
sudo apt install bridge-utils 
sudo apt install libvirt-daemon-system
sudo apt install libvirt-clients
```
##Restart Libvirt Service
```bash
sudo service libvirtd restart
```
## Make Directory for Images Pool
```bash
sudo mkdir -p /home/fwutech/Qemu/imgs
```
## Delete Default pool
```bash
virsh pool-destroy default
virsh pool-undefine default
```
## Add and Define KVM pool in new path (/home/fwutech/Qemu/imgs)
```bash
virsh pool-define-as --name KVM --type dir --target /home/fwutech/Qemu/imgs
virsh pool-autostart KVM
virsh pool-start KVM
```
## Add and define Network (We should define two network: NAT and Isolated network )
```bash
virsh net-destroy default
virsh net-undefine default
```