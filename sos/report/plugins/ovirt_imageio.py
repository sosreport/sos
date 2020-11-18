# Copyright (C) 2014 Red Hat, Inc., Sandro Bonazzola <sbonazzo@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class OvirtImageIO(Plugin, RedHatPlugin):

    short_desc = 'oVirt Image I/O Daemon / Proxy'

    packages = (
        'ovirt-imageio-daemon',
        'ovirt-imageio-proxy',
    )

    plugin_name = 'ovirt_imageio'
    profiles = ('virt',)

    def setup(self):
        all_logs = self.get_option('all_logs')

        # Add configuration files
        self.add_copy_spec([
            '/etc/ovirt-imageio-daemon/logger.conf',
            '/etc/ovirt-imageio-daemon/daemon.conf',
            '/etc/ovirt-imageio-proxy/ovirt-imageio-proxy.conf',
            '/etc/ovirt-imageio/conf.d/*.conf',
        ])

        if all_logs:
            logs = ['/var/log/ovirt-imageio-proxy/image-proxy.log*',
                    '/var/log/ovirt-imageio-daemon/daemon.log*',
                    '/var/log/ovirt-imageio/daemon.log*']
        else:
            logs = ['/var/log/ovirt-imageio-proxy/image-proxy.log',
                    '/var/log/ovirt-imageio-daemon/daemon.log',
                    '/var/log/ovirt-imageio/daemon.log']

        # Add log files
        self.add_copy_spec(logs)


# vim: expandtab tabstop=4 shiftwidth=4
