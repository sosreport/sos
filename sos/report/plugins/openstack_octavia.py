# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class OpenStackOctavia(Plugin):

    short_desc = 'Openstack Octavia'

    plugin_name = "openstack_octavia"
    profiles = ('openstack', 'openstack_controller')

    var_config_data = "/var/lib/config-data"
    var_puppet_gen = var_config_data + "/puppet-generated/octavia"

    resources = [
        'amphora',
        'availabilityzone',
        'availabilityzoneprofile',
        'flavor',
        'flavorprofile',
        'healthmonitor',
        'l7policy',
        'listener',
        'pool',
        'provider',
        'quota'
    ]

    def setup(self):
        # configs
        self.add_copy_spec([
            "/etc/sysconfig/network-scripts/ifcfg-o-hm0",
            "/etc/logrotate.d/openstack-octavia",
            "/etc/octavia/*",
            "/var/lib/octavia",
            self.var_config_data + "/octavia/etc/octavia",
            self.var_puppet_gen + "/etc/octavia",
            self.var_puppet_gen + "/etc/rsyslog.d",
            self.var_puppet_gen + "/etc/my.cnf.d/tripleo.cnf",
        ])

        # don't collect certificates
        self.add_forbidden_path("/etc/octavia/certs")
        self.add_forbidden_path(self.var_config_data + "/etc/octavia/certs")
        self.add_forbidden_path(self.var_puppet_gen + "/etc/octavia/certs")

        # logs
        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/octavia/*",
            ])
        else:
            self.add_copy_spec([
                "/var/log/octavia/*.log",
            ])

    def postproc(self):
        protect_keys = [
            "ca_private_key_passphrase", "heartbeat_key", "password",
            "connection", "transport_url", "server_certs_key_passphrase"
        ]
        regexp = r"((?m)^\s*(%s)\s*=\s*)(.*)" % "|".join(protect_keys)

        self.do_path_regex_sub("/etc/octavia/*", regexp, r"\1*********")
        self.do_path_regex_sub(
            self.var_puppet_gen + "/etc/octavia/*",
            regexp, r"\1*********"
        )


class DebianOctavia(OpenStackOctavia, DebianPlugin, UbuntuPlugin):

    packages = ('octavia-common', 'octavia-api', )

    def setup(self):
        super(DebianOctavia, self).setup()
        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/apache2/octavia*",
            ])
        else:
            self.add_copy_spec([
                "/var/log/apache2/octavia*.log",
            ])


class RedHatOctavia(OpenStackOctavia, RedHatPlugin):

    packages = ('openstack-selinux',)

# vim: set et ts=4 sw=4 :
