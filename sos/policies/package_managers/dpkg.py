# Copyright 2020 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.policies.package_managers import PackageManager


class DpkgPackageManager(PackageManager):
    """Subclass for dpkg-based distrubitons
    """

    query_command = "dpkg-query -W -f='${Package}|${Version}\\n'"
    verify_command = "dpkg --verify"
    verify_filter = ""


# vim: set et ts=4 sw=4 :
