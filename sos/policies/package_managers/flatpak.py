# Copyright 2023 Red Hat, Inc. Jose Castillo <jcastillo@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.policies.package_managers import PackageManager


class FlatpakPackageManager(PackageManager):
    """Package Manager for Flatpak distributions
    """

    query_command = 'flatpak list --columns=name,version,branch'
    query_path_command = ''
    files_command = ''
    verify_command = ''
    verify_filter = ''

    def _parse_pkg_list(self, pkg_list):
        for line in pkg_list.splitlines():
            pkg = line.split("\t")
            yield (pkg[0], pkg[1], pkg[2])

# vim: set et ts=4 sw=4 :
