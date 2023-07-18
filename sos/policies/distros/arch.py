# Copyright 2023 Marcel Wiegand <wiegand@linux.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import ArchPlugin
from sos.policies.distros import LinuxPolicy
from sos.policies.package_managers.pacman import PacmanPackageManager


class ArchPolicy(LinuxPolicy):
    distro = "Arch Linux"
    vendor = "Arch Linux"
    vendor_urls = [("Community Website", "https://www.archlinux.org/")]
    os_release_name = 'Arch Linux'
    os_release_id = 'arch'

    def __init__(
        self, sysroot=None, init=None, probe_runtime=True, remote_exec=None
    ):
        super().__init__(
            sysroot=sysroot,
            init=init,
            probe_runtime=probe_runtime,
            remote_exec=remote_exec,
        )
        self.package_manager = PacmanPackageManager(
            chroot=self.sysroot, remote_exec=remote_exec
        )
        self.valid_subclasses += [ArchPlugin]
