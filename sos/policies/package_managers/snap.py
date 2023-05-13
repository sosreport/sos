# Copyright 2023 Canonical Ltd. Arif Ali <arif.ali@canonical.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.policies.package_managers import PackageManager


class SnapPackageManager(PackageManager):
    """Subclass for snap-based distributions
    """

    query_command = "snap list"
    query_path_command = ""
    verify_command = ""
    verify_filter = ""

    def _parse_pkg_list(self, pkg_list):
        for line in pkg_list.splitlines():
            if line == "":
                continue
            pkg = line.split()
            if pkg[0] == "Name" or pkg[0] == "Connection":
                continue
            name, version = pkg[0], pkg[1]
            yield (name, version, None)

# vim: set et ts=4 sw=4 :
