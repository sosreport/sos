# Copyright (C) Eduard Abdullin <eabdullin@almalinux.org>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.policies.distros.redhat import RedHatPolicy


class AlmaLinuxPolicy(RedHatPolicy):
    vendor = "AlmaLinux OS Foundation"
    os_release_file = '/etc/almalinux-release'
    os_release_name = 'AlmaLinux'

    vendor_urls = [
        ('Distribution Website', 'https://www.almalinux.org/'),
        ('Commercial Support', 'https://tuxcare.com/linux-support-services/')
    ]

    def __init__(self, sysroot=None, init=None, probe_runtime=True,
                 remote_exec=None):
        super().__init__(sysroot=sysroot, init=init,
                         probe_runtime=probe_runtime,
                         remote_exec=remote_exec)

# vim: set et ts=4 sw=4 :
