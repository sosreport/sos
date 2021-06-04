# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin
from glob import glob


class Puppet(Plugin, IndependentPlugin):

    short_desc = 'Puppet service'

    plugin_name = 'puppet'
    profiles = ('services',)
    packages = ('puppet', 'puppet-common', 'puppet-server',
                'puppetserver', 'puppetmaster', 'puppet-master')

    def setup(self):
        _hostname = self.exec_cmd('hostname')['output']
        _hostname = _hostname.strip()

        self.add_copy_spec([
            "/etc/puppet/*.conf",
            "/etc/puppet/rack/*",
            "/etc/puppet/manifests/*",
            "/etc/puppet/ssl/ca/inventory.txt",
            "/var/log/puppet/*.log*",
            "/etc/puppetlabs/puppet/*.conf",
            "/etc/puppetlabs/puppetserver/conf.d/*.conf",
            "/etc/puppetlabs/puppet/rack/*",
            "/etc/puppetlabs/puppet/manifests/*",
            "/etc/puppetlabs/puppet/ssl/ca/inventory.txt",
            "/var/log/puppetlabs/puppetserver/*.log*",
            "/var/lib/puppetlabs/puppet/ssl/ca/inventory.txt",
            "/var/lib/puppet/ssl/ca/inventory.txt",
            "/var/lib/puppet/ssl/certs/ca.pem",
            "/etc/puppetlabs/puppet/ssl/certs/ca.pem",
            "/etc/puppetlabs/puppet/ssl/certs/{}.pem".format(_hostname),
            "/var/lib/puppet/ssl/certs/{}.pem".format(_hostname),
        ])

        self.add_cmd_output([
            'facter',
            'puppet --version',
            'ls -lanR /etc/puppet/modules',
            'ls -lanR /etc/puppetlabs/code/modules'
        ])

    def postproc(self):
        for device_conf in glob("/etc/puppet/device.conf*"):
            self.do_file_sub(
                device_conf,
                r"(.*url*.ssh://.*:).*(@.*)",
                r"\1%s\2" % ('***')
            )

        return
# vim: et ts=4 sw=4
