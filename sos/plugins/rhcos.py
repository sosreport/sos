# Copyright (C) 2019 Red Hat, Inc., Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin


class RHCoreOS(Plugin, RedHatPlugin):
    """Red Hat CoreOS"""

    plugin_name = 'rhcos'
    packages = ('redhat-release-coreos', 'coreos-metadata')

    def setup(self):
        units = ['coreos-growpart', 'coreos-firstboot-complete']
        for unit in units:
            self.add_journal(unit)

        self.add_cmd_output(
            'coreos-metadata --cmdline --attributes /dev/stdout',
            timeout=60
        )

# vim: set et ts=4 sw=4 :
