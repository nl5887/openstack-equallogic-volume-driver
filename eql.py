#!/usr/bin/python

# vim: tabstop=4 shiftwidth=4 softtabstop=4
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
Drivers for Dell Equallogic stored volumes.

The unique thing about a SAN is that we don't expect that we can run the volume
controller on the SAN hardware.  We expect to access it over SSH or some API.
"""

import os
import paramiko

import sys
import re

import eqlscript

from xml.etree import ElementTree

from nova import exception
from nova import flags
from nova import log as logging
from nova.utils import ssh_execute
from nova.volume.driver import ISCSIDriver
from nova.volume.san import SanISCSIDriver


from nova import flags
from nova import log as logging
from nova import service
from nova import utils


LOG = logging.getLogger("nova.volume.driver.eql")
FLAGS = flags.FLAGS
#flags.DEFINE_boolean('san_thin_provision', 'true',
#                     'Use thin provisioning for SAN volumes?')
#flags.DEFINE_string('san_ip', '',
#                    'IP address of SAN controller')
#flags.DEFINE_string('san_login', 'grpadmin',
#                    'Username for SAN controller')
#flags.DEFINE_string('san_password', '',
#                    'Password for SAN controller')
#flags.DEFINE_string('san_privatekey', '',
#                    'Filename of private key to use for SSH authentication')
#flags.DEFINE_string('san_clustername', '',
#                    'Cluster name to use for creating volumes')
#flags.DEFINE_integer('san_ssh_port', 22,
#                    'SSH port to use with SAN')

class EqlISCSIDriver(SanISCSIDriver):
    def create_volume(self, volume):
	model_update = {}

	remote = eqlscript.session (FLAGS.san_ip, FLAGS.san_login, FLAGS.san_password, False)

	volName = volume['name']
		
	if int(volume['size']) == 0:
		volSize = '100MB'
        else:
		volSize = '%sGB' % volume['size']

	result = remote.cmd ("vol create %s %s %s unrestricted" % (volName, volSize, "thin-provision" if FLAGS.san_thin_provision else ""))
	print "".join(result)
	if remote.err ():
		print "".join(remote.err())
		raise exception.Error(_("Failed to create volume %s size %s with error %s" %  volName, volSize, "".join (remote.err ())))
	targre = re.compile (r"iscsi target name is\s+(.*)$", re.I | re.M)
	m = targre.search ("".join (result))
	if m:
		cluster_interface = '1'
		cluster_vip = FLAGS.san_ip
		iscsi_portal = cluster_vip + ":3260," + cluster_interface
		iscsi_iqn = m.group (1)
	
		model_update['provider_location'] = ("%s %s" %
							 (iscsi_portal,
							  iscsi_iqn))
										  
		#
		# Dump information about the volume
		#
		result = remote.cmd ("vol sel %s show" % volName)
		if remote.err ():
			raise exception.Error(_("Failed to show information about volume %s " %  volName, "".join (remote.err ())))

		remote.logout ()

		return model_update

    def delete_volume(self, volume):
        """Deletes a volume."""
	remote = eqlscript.session (FLAGS.san_ip, FLAGS.san_login, FLAGS.san_password, False)
		
#		result = remote.cmd ("vol delete %s" % (volume['name']))
#		result = remote.read_until ("Do you really want to delete the volume")
#		remote.write ("y\r")

	remote.logout ()

    def local_path(self, volume):
	print "Localpath"
        # TODO(justinsb): Is this needed here?
        raise exception.Error(_("local_path not supported"))

    def ensure_export(self, context, volume):
        """Synchronously recreates an export for a logical volume."""
        return self._do_export(context, volume, force_create=False)

    def create_snapshot(self, snapshot):
	model_update = {}

	remote = eqlscript.session (FLAGS.san_ip, FLAGS.san_login, FLAGS.san_password, False)

	print ("Creating snapshot %s" % snapshot['name'])
	
	result = remote.cmd ("volume select %s clone %s description \"clone of volume %s\" unrestricted" % (snapshot['volume_name'], snapshot['name'], snapshot['volume_name']))
	if remote.err ():
		raise exception.Error(_("Failed to create snapshot %s of volume %s error %s" %  snapshot['name'], snapshot['volume_name'], "".join (remote.err ())))

	remote.logout ()

	return model_update

    def delete_snapshot(self, snapshot):
	#
        """Supports ensure_export and create_export"""
	remote = eqlscript.session (FLAGS.san_ip, FLAGS.san_login, FLAGS.san_password, False)
        # assign volume
        # currently not necessary, because unrestricted
	#result = remote.cmd ("show pool")

	#if remote.err ():
	#	raise exception.Error(_("error %s" % "".join (remote.err ())))

	print "".join(result)

	remote.logout ()

    def create_volume_from_snapshot(self, volume, snapshot):
	model_update = {}

	remote = eqlscript.session (FLAGS.san_ip, FLAGS.san_login, FLAGS.san_password, False)

	print ("Creating volume %s from snapshot %s" % (volume['name'], snapshot['name']))
	
	result = remote.cmd ("volume select %s clone %s description \"clone of snapshot volume %s\" unrestricted" % (snapshot['name'], volume['name'], snapshot['volume_name']))
	if remote.err ():
		raise exception.Error(_("Failed to create volume %s of snapshot %s error %s" %  (volume['name'], snapshot['name'], "".join (remote.err ()))))
	print "".join(result)
	
	LOG.info("".join(result))
	
	targre = re.compile (r"is\s+([\w\d.-]+\:[0123456789abcdef]\-[0123456789abcdef]+\-[0123456789abcdef]+\-[0123456789abcdef]+\-[\w\d-]+)cloning", re.I | re.M)
	m = targre.search ("".join(result))
	if m:
		cluster_interface = '1'
		cluster_vip = FLAGS.san_ip
		iscsi_portal = cluster_vip + ":3260," + cluster_interface
		iscsi_iqn = m.group (1)
	
		model_update['provider_location'] = ("%s %s" %
							 (iscsi_portal,
							  iscsi_iqn))

		#
		# Dump information about the volume
		#
		result = remote.cmd ("vol sel %s show" % volume['name'])
		if remote.err ():
			raise exception.Error(_("Failed to show information about volume %s " %  volName, "".join (remote.err ())))

		remote.logout ()

		return model_update


    def create_export(self, context, volume):
	# we can do an vol sel show and update the provider_location here
        return self._do_export(context, volume, force_create=True)

    def _do_export(self, context, volume, force_create):
	print "Do export for volume"

        """Supports ensure_export and create_export"""
	remote = eqlscript.session (FLAGS.san_ip, FLAGS.san_login, FLAGS.san_password, False)
        # assign volume
        # currently not necessary, because unrestricted
	result = remote.cmd ("show pool")

	#if remote.err ():
	#	raise exception.Error(_("error %s" % "".join (remote.err ())))

	print "".join(result)

	remote.logout ()

        model_update = {}
        return model_update

    def remove_export(self, context, volume):
        """Removes an export for a logical volume."""
	print "Remove export for volume"
	remote = eqlscript.session (FLAGS.san_ip, FLAGS.san_login, FLAGS.san_password, False)
	# unassign volume
        # currently not necessary, because unrestricted
	remote.logout ()

if __name__ == "__main__":
	utils.default_flagfile()
	flags.FLAGS(sys.argv)
	logging.setup()
	print FLAGS.san_ip
  	"""Supports ensure_export and create_export"""
	remote = eqlscript.session (FLAGS.san_ip, FLAGS.san_login, FLAGS.san_password, False)
	remote.logout ()

