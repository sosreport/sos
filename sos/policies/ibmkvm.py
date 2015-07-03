# Copyright (C) IBM Corporation, 2015
#
# Authors: Kamalesh Babulal <kamalesh@linux.vnet.ibm.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
from __future__ import print_function

from sos.plugins import PowerKVMPlugin, ZKVMPlugin, RedHatPlugin
from sos.policies.redhat import RedHatPolicy

import os


class PowerKVMPolicy(RedHatPolicy):
    distro = "PowerKVM"
    vendor = "IBM"
    vendor_url = "http://www-03.ibm.com/systems/power/software/linux/powerkvm"

    def __init__(self):
        super(PowerKVMPolicy, self).__init__()
        self.valid_subclasses = [PowerKVMPlugin, RedHatPlugin]

    @classmethod
    def check(self):
        """This method checks to see if we are running on PowerKVM.
           It returns True or False."""
        return os.path.isfile('/etc/ibm_powerkvm-release')

    def dist_version(self):
        try:
            with open('/etc/ibm_powerkvm-release', 'r') as fp:
                version_string = fp.read()
                return version_string[2][0]
            return False
        except:
            return False


class ZKVMPolicy(RedHatPolicy):
    distro = "IBM Hypervisor"
    vendor = "IBM Hypervisor"
    vendor_url = "http://www.ibm.com/systems/z/linux/IBMHypervisor/support/"

    def __init__(self):
        super(ZKVMPolicy, self).__init__()
        self.valid_subclasses = [ZKVMPlugin, RedHatPlugin]

    @classmethod
    def check(self):
        """This method checks to see if we are running on IBM Z KVM. It
        returns True or False."""
        return os.path.isfile('/etc/base-release')

    def dist_version(self):
        try:
            with open('/etc/base-release', 'r') as fp:
                version_string = fp.read()
                return version_string.split(' ', 4)[3][0]
            return False
        except:
            return False


# vim: set ts=4 sw=4
