# Copyright (C) 2012 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Upstart(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Upstart init system
    """

    plugin_name = 'upstart'
    profiles = ('system', 'services', 'boot')
    packages = ('upstart',)

    def setup(self):
        self.add_cmd_output([
            'initctl --system list',
            'initctl --system version',
            'init --version',
            "ls -l /etc/init/",
            'initctl show-config'
        ])

        # Job Configuration Files
        self.add_copy_spec([
            '/etc/init.conf',
            '/etc/event.d/*',
            '/etc/init/*.conf'
        ])

        # State file
        self.add_copy_spec('/var/log/upstart/upstart.state')

        # Log files
        self.add_copy_spec('/var/log/upstart/*')
        # Session Jobs (running Upstart as a Session Init)
        self.add_copy_spec('/usr/share/upstart/')


# vim: set et ts=4 sw=4 :
