# Copyright (C) 2007 Red Hat, Inc., Eugene Teo <eteo@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Ssh(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Secure shell service
    """

    plugin_name = 'ssh'
    profiles = ('services', 'security', 'identity')

    def setup(self):
        self.add_copy_spec([
            "/etc/ssh/ssh_config",
            "/etc/ssh/sshd_config"
        ])

# vim: set et ts=4 sw=4 :
