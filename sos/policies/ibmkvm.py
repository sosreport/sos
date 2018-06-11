# Copyright (C) IBM Corporation, 2015
#
# Authors: Kamalesh Babulal <kamalesh@linux.vnet.ibm.com>
#
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from __future__ import print_function

from sos.plugins import PowerKVMPlugin, ZKVMPlugin, RedHatPlugin
from sos.policies.redhat import RedHatPolicy

import os


class PowerKVMPolicy(RedHatPolicy):
    distro = "PowerKVM"
    vendor = "IBM"
    vendor_url = "http://www-03.ibm.com/systems/power/software/linux/powerkvm"

    def __init__(self, sysroot=None):
        super(PowerKVMPolicy, self).__init__(sysroot=sysroot)
        self.valid_subclasses = [PowerKVMPlugin, RedHatPlugin]

    @classmethod
    def check(cls):
        """This method checks to see if we are running on PowerKVM.
           It returns True or False."""
        return os.path.isfile('/etc/ibm_powerkvm-release')

    def dist_version(self):
        try:
            with open('/etc/ibm_powerkvm-release', 'r') as fp:
                version_string = fp.read()
                return version_string[2][0]
            return False
        except IOError:
            return False


class ZKVMPolicy(RedHatPolicy):
    distro = "IBM Hypervisor"
    vendor = "IBM Hypervisor"
    vendor_url = "http://www.ibm.com/systems/z/linux/IBMHypervisor/support/"

    def __init__(self, sysroot=None):
        super(ZKVMPolicy, self).__init__(sysroot=sysroot)
        self.valid_subclasses = [ZKVMPlugin, RedHatPlugin]

    @classmethod
    def check(cls):
        """This method checks to see if we are running on IBM Z KVM. It
        returns True or False."""
        return os.path.isfile('/etc/base-release')

    def dist_version(self):
        try:
            with open('/etc/base-release', 'r') as fp:
                version_string = fp.read()
                return version_string.split(' ', 4)[3][0]
            return False
        except IOError:
            return False


# vim: set ts=4 sw=4
