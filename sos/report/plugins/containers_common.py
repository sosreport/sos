# Copyright (C) 2020 Red Hat, Inc., Pavel Moravec <pmoravec@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, UbuntuPlugin


class ContainersCommon(Plugin, RedHatPlugin, UbuntuPlugin):

    short_desc = 'Common container configs under {/etc,/usr/share}/containers'
    plugin_name = 'containers_common'
    profiles = ('container', )
    packages = ('containers-common', )

    def setup(self):
        self.add_copy_spec([
            '/etc/containers/*',
            '/usr/share/containers/*',
        ])

# vim: set et ts=4 sw=4 :
