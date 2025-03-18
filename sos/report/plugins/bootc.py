# Copyright (C) 2024 Red Hat, Inc., Jose Castillo <jcastillo@redhat.com>
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class Bootc(Plugin, RedHatPlugin):

    short_desc = 'Bootc'

    plugin_name = 'bootc'
    profiles = ('system', 'sysmgmt', 'packagemanager',)

    packages = ('bootc',)

    def setup(self):
        self.add_copy_spec([
            "/usr/lib/ostree/prepare-root.conf",
            "/usr/lib/bootc/",
        ])

        self.add_cmd_output(
            "bootc status",
        )

        self.add_forbidden_path("/usr/lib/bootc/storage")

# vim: set et ts=4 sw=4 :
