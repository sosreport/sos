# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class OpenStackDesignate(Plugin):

    short_desc = 'Openstack Designate'

    plugin_name = "openstack_designate"
    profiles = ('openstack', 'openstack_controller')

    var_puppet_gen = "/var/lib/config-data/puppet-generated/designate"

    def setup(self):
        # configs
        self.add_copy_spec([
            "/etc/designate/*",
            self.var_puppet_gen + "/etc/designate/designate.conf",
            self.var_puppet_gen + "/etc/designate/pools.yaml",
        ])

        # logs
        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/designate/*",
                "/var/log/containers/designate/*",
            ])
        else:
            self.add_copy_spec([
                "/var/log/designate/*.log",
                "/var/log/containers/designate/*.log"
            ])

    def postproc(self):
        protect_keys = [
            "password", "connection", "transport_url", "admin_password",
            "ssl_key_password", "ssl_client_key_password",
            "memcache_secret_key"
        ]
        regexp = r"((?m)^\s*(%s)\s*=\s*)(.*)" % "|".join(protect_keys)

        self.do_path_regex_sub("/etc/designate/*", regexp, r"\1*********")
        self.do_path_regex_sub(
            self.var_puppet_gen + "/etc/designate/*",
            regexp, r"\1*********"
        )


class RedHatdesignate(OpenStackDesignate, RedHatPlugin):

    packages = ('openstack-selinux',)

# vim: set et ts=4 sw=4 :
