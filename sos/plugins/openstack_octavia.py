# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class OpenStackOctavia(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Openstack Octavia"""

    plugin_name = "openstack_octavia"
    profiles = ('openstack', 'openstack_controller')
    packages = ('openstack-octavia-common',)

    var_puppet_gen = "/var/lib/config-data/puppet-generated/octavia"

    def setup(self):
        # configs
        self.add_copy_spec([
            "/etc/sysconfig/network-scripts/ifcfg-o-hm0",
            "/etc/logrotate.d/openstack-octavia",
            "/etc/octavia/*",
            "/var/lib/octavia",
            self.var_puppet_gen + "/etc/octavia/conf.d",
            self.var_puppet_gen + "/etc/octavia/octavia.conf",
            self.var_puppet_gen + "/etc/my.cnf.d/tripleo.cnf",
        ])

        # don't collect certificates
        self.add_forbidden_path("/etc/octavia/certs/")

        # logs
        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/containers/httpd/octavia-api/*",
                "/var/log/containers/octavia/*",
                "/var/log/octavia/*",
            ])
        else:
            self.add_copy_spec([
                "/var/log/containers/httpd/octavia-api/*.log",
                "/var/log/containers/octavia/*.log",
                "/var/log/octavia/*.log",
            ])

        # commands
        self.add_cmd_output([
            "openstack loadbalancer list",
            "openstack loadbalancer amphora list",
            "openstack loadbalancer healthmonitor list",
            "openstack loadbalancer l7policy list",
            "openstack loadbalancer listener list",
            "openstack loadbalancer pool list",
            "openstack loadbalancer quota list",
        ])

        # get details from each loadbalancer
        cmd = "openstack loadbalancer list -f value -c id"
        loadbalancers = self.call_ext_prog(cmd)['output']
        for loadbalancer in loadbalancers.splitlines():
            loadbalancer = loadbalancer.split()[0]
            self.add_cmd_output(
                "openstack loadbalancer show %s" % (loadbalancer)
            )

        # get details from each l7policy
        cmd = "openstack loadbalancer l7policy list -f value -c id"
        l7policies = self.call_ext_prog(cmd)['output']
        for l7policy in l7policies.splitlines():
            l7policy = l7policy.split()[0]
            self.add_cmd_output(
                "openstack loadbalancer l7rule list %s" % (l7policy)
            )

        # get details from each pool
        cmd = "openstack loadbalancer pool list -f value -c id"
        pools = self.call_ext_prog(cmd)['output']
        for pool in pools.splitlines():
            pool = pool.split()[0]
            self.add_cmd_output(
                "openstack loadbalancer member list %s" % (pool)
            )

        if self.get_option("verify"):
            self.add_cmd_output("rpm -V %s" % ' '.join(self.packages))

    def postproc(self):
        protect_keys = [
            "ca_private_key_passphrase", "heartbeat_key", "password",
            "connection"
        ]
        regexp = r"((?m)^\s*(%s)\s*=\s*)(.*)" % "|".join(protect_keys)

        self.do_path_regex_sub("/etc/octavia/*", regexp, r"\1*********")
        self.do_path_regex_sub(
            self.var_puppet_gen + "/etc/octavia/*",
            regexp, r"\1*********"
        )

# vim: set et ts=4 sw=4 :
