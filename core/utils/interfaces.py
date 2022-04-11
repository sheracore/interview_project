def netmask_to_cidr(netmask):
    """
    netmask: netmask ip addr (eg: 255.255.255.0)
    return: equivalent cidr number to given netmask ip (eg: 24)
    """
    return sum([bin(int(x)).count('1') for x in netmask.split('.')])
