# Copyright (C) 2014 Red Hat, Inc., Sandro Bonazzola <sbonazzo@redhat.com>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.


import glob


from sos.plugins import Plugin, RedHatPlugin


class OvirtImageIO(Plugin, RedHatPlugin):
    """oVirt Image I/O Daemon / Proxy"""

    packages = (
        'ovirt-imageio-daemon',
        'ovirt-imageio-proxy',
    )

    plugin_name = 'ovirt_imageio'
    profiles = ('virt',)

    def setup(self):
        self.limit = self.get_option('log_size')
        all_logs = self.get_option('all_logs')

        # Add configuration files
        self.add_copy_spec([
            '/etc/ovirt-imageio-daemon/logger.conf',
            '/etc/ovirt-imageio-proxy/ovirt-imageio-proxy.conf',
        ])

        if all_logs:
            logs = ['/var/log/ovirt-imageio-proxy/image-proxy.log*',
                    '/var/log/ovirt-imageio-daemon/daemon.log*']
        else:
            logs = ['/var/log/ovirt-imageio-proxy/image-proxy.log',
                    '/var/log/ovirt-imageio-daemon/daemon.log']

        # Add log files
        self.add_copy_spec(logs, sizelimit=self.limit)


# vim: expandtab tabstop=4 shiftwidth=4
