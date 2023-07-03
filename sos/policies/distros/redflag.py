# Copyright (c) Yang Qing <yangqing@redflag-os.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.policies.distros.redhat import RedHatPolicy, OS_RELEASE
import os


class RedFlagPolicy(RedHatPolicy):
    distro = "Red Flag Asianux Server Linux"
    vendor = "Red Flag Software"
    vendor_urls = [('Distribution Website', 'http://www.redflag-os.com')]

    def __init__(self, sysroot=None, init=None, probe_runtime=True,
                 remote_exec=None):
        super(RedFlagPolicy, self).__init__(sysroot=sysroot, init=init,
                                            probe_runtime=probe_runtime,
                                            remote_exec=remote_exec)

    @classmethod
    def check(cls, remote=''):
        if remote:
            return cls.distro in remote

        # Return False if /etc/os-release is missing
        if not os.path.exists(OS_RELEASE):
            return False

        # Return False if /etc/redflag-release is missing
        if not os.path.isfile('/etc/redflag-release'):
            return False

        # Check RedFlag in /etc/os-release
        with open(OS_RELEASE, 'r') as f:
            for line in f:
                if line.startswith('NAME'):
                    if 'Red Flag Asianux Server' in line:
                        return True

        return False

# vim: set et ts=4 sw=4 :
