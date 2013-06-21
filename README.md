openstack-equallogic-volume-driver
==================================
Dell Equallogic volume driver voor Openstack

### Install
#### Download and install eqlscript (from Host Integration Tools for Linux)
 * cd /root/eqlscript-1.0/)
 * python setup.py install

#### Install paramiko
 * apt-get install python-paramiko

#### Install eql volume driver
 * scp /usr/share/pyshared/nova/volume/eql.py /usr/share/pyshared/nova/volume/
 * ln -s /usr/share/pyshared/nova/volume/eql.py /usr/lib/python2.6/dist-packages/nova/volume/
 * ln -s /usr/share/pyshared/nova/volume/eql.py /usr/lib/python2.7/dist-packages/nova/volume/

#### Configuration (nova.conf)
```
--volume_driver=nova.volume.eql.EqlISCSIDriver
--san_ip={ip}
--san_login={login}
--san_password={password}
```

#### Restart volume services
 * service nova-volume restart
 
### Requirements
 * Host Integration Tools for Linux (http://support.equallogic.com)
 * Paramiko
 
### Disclaimer
We've used this volume driver for a few years now, and have no problems or issues with it. Permission for use of this software is granted only if the user accepts
full responsibility for any undesirable consequences; the authors accept NO LIABILITY for damages of any kind.