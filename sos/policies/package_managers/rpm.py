# Copyright 2020 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.policies.package_managers import PackageManager


class RpmPackageManager(PackageManager):
    """Package Manager for RPM-based distributions
    """

    query_command = 'rpm -qa --queryformat "%{NAME}|%{VERSION}|%{RELEASE}\\n"'
    query_path_command = 'rpm -qf'
    files_command = 'rpm -qal'
    verify_command = 'rpm -V'
    verify_filter = ["debuginfo", "-devel"]

    def _parse_pkg_list(self, pkg_list):
        for pkg in pkg_list.splitlines():
            if '|' not in pkg:
                continue
            name, version, release = pkg.split('|')
            yield (name, version, release)

# vim: set et ts=4 sw=4 :
