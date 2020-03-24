# Copyright (C) 2007 Red Hat, Inc., Eugene Teo <eteo@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Xinetd(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """xinetd information
    """

    plugin_name = 'xinetd'
    profiles = ('services', 'network', 'boot')

    files = ('/etc/xinetd.conf',)
    packages = ('xinetd',)

    def setup(self):
        self.add_copy_spec([
            "/etc/xinetd.conf",
            "/etc/xinetd.d"
        ])

# vim: set et ts=4 sw=4 :
