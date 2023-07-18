# Copyright 2023 Marcel Wiegand <wiegand@linux.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.policies.package_managers import PackageManager


class PacmanPackageManager(PackageManager):
    """Subclass for pacman-based distributions"""

    query_command = "pacman -Q"
    query_path_command = "pacman -Qo"
    verify_command = "pacman -Qk"
    verify_filter = ""

    def _parse_pkg_list(self, pkg_list):
        for pkg in pkg_list.splitlines():
            name, version = pkg.split(" ")
            yield (name, version, None)
