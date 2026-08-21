# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from glob import glob
from sos.report.plugins import Plugin, IndependentPlugin
import os

class Puppet(Plugin, IndependentPlugin):

    short_desc = 'Pupppet/Openvox services'

    plugin_name = 'puppet'
    profiles = ('services',)
    packages = ('openvox-agent', 'openvox-server', 'openvoxdb',
                'puppet', 'puppet-agent', 'puppet-common', 'puppet-server',
                'puppetserver', 'puppetmaster', 'puppet-master', 'puppetdb')
    services = ('puppet', 'puppetserver', 'puppetdb')

    def setup(self):
        _hostname = self.exec_cmd('hostname')['output']
        _hostname = _hostname.strip()
        curl = '/opt/puppetlabs/puppet/bin/curl'
        openssl = '/opt/puppetlabs/puppet/bin/openssl'
        self.add_default_cmd_environment({
            'PATH': os.environ['PATH'] + ':/opt/puppetlabs/bin'
        })

        self.add_copy_spec([
            # Agent
            "/etc/puppet/*.conf",
            "/etc/puppet/hiera.yaml",
            "/etc/puppet/rack/*",
            "/etc/puppet/manifests/*",
            "/etc/puppetlabs/puppet/*.conf",
            "/etc/puppetlabs/puppet/hiera.yaml",
            "/etc/puppetlabs/puppet/routes.yaml",
            # Server
            "/etc/puppetlabs/puppetserver/*.xml",
            "/etc/puppetlabs/puppetserver/conf.d/*",
            "/etc/puppetlabs/puppetserver/services.d/*",
            # Database
            "/etc/puppetlabs/puppetdb/*.cfg",
            "/etc/puppetlabs/puppetdb/*.xml",
            "/etc/puppetlabs/puppetdb/conf.d/*",
            # Code
            "/etc/puppetlabs/code/hiera.yaml",
            "/etc/puppetlabs/r10k/r10k.yaml",
            # Startup
            "/etc/sysconfig/puppet*",
            "/etc/default/pupppet*",
            # State
            "/opt/puppetlabs/puppet/cache/state/*.txt",
            "/opt/puppetlabs/puppet/cache/state/*.lock",
            "/opt/puppetlabs/puppet/cache/state/*.yaml",
            "/opt/puppetlabs/puppet/public/last_run_summary.yaml",
            # Logs
            "/var/log/puppet/*.log*",
            "/var/log/puppetlabs/puppet/*.log*",
            "/var/log/puppetlabs/puppetdb/*.log*",
            "/var/log/puppetlabs/puppetserver/*.log*",
            # Certs/Inventory
            "/etc/puppetlabs/puppet/ssl/ca/ca_crl.pem",
            "/etc/puppetlabs/puppet/ssl/ca/ca_crt.pem",
            "/etc/puppetlabs/puppet/ssl/ca/inventory.txt",
            "/var/lib/puppetlabs/puppet/ssl/ca/inventory.txt",
            "/var/lib/puppet/ssl/ca/inventory.txt",
            "/var/lib/puppet/ssl/certs/ca.pem",
            f"/etc/puppetlabs/puppet/ssl/certs/{_hostname}.pem",
            f"/var/lib/puppet/ssl/certs/{_hostname}.pem",
        ])
        self.add_copy_spec("/etc/puppetlabs/puppet/ssl/certs/ca.pem",
                           tags="puppet_ssl_cert_ca_pem")

        self.add_cmd_output([
            # Agent
            'facter',
            'puppet --version',
            'puppet config print --section main',
            '/opt/puppetlabs/puppet/bin/gem list --local',
            # Server
            'puppet config print --section server',
            'puppetserver --version',
            'puppetserver gem list --local',
            # Code
            'puppet module list --tree',
            # State
            curl + ' -k https://localhost:8140/status/v1/services?level=debug',
            curl + ' http://localhost:8080/pdb/admin/v1/summary-stats',
            curl + ' http://localhost:8080/status/v1/services?level=debug',
            # Certs/Inventory
            openssl + ' x509 -in /etc/puppetlabs/puppet/ssl/ca/ca_crt.pem -noout -dates -subject',
            openssl + ' x509 -in /etc/puppetlabs/puppet/ssl/certs/ca.pem -noout -dates -subject',
            openssl + ' crl -in /etc/puppetlabs/puppet/ssl/crl.pem -noout -lastupdate -nextupdate -issuer -crlnumber',
        ])

        self.add_dir_listing([
            '/etc/puppet/modules',
            '/etc/puppetlabs/code/modules'
        ], recursive=True)

    def postproc(self):
        for device_conf in glob("/etc/puppet/device.conf*"):
            self.do_file_sub(
                device_conf,
                r"(.*url*.ssh://.*:).*(@.*)",
                r"\1***\2"
            )

# vim: et ts=4 sw=4
