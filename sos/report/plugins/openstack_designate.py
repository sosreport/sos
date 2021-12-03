# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, UbuntuPlugin


class OpenStackDesignate(Plugin):

    short_desc = 'Openstack Designate'

    plugin_name = "openstack_designate"
    profiles = ('openstack', 'openstack_controller')

    var_puppet_gen = "/var/lib/config-data/puppet-generated/designate"

    def setup(self):
        # collect current pool config

        self.add_cmd_output(
            "designate-manage pool generate_file --file /dev/stdout",
            container=self.get_container_by_name(".*designate_central"),
            suggest_filename="openstack_designate_current_pools.yaml"
        )

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

        subcmds = [
            'dns service list',
            'dns quota list',
            'ptr record list',
            'tld list',
            'tsigkey list --column name --column algorithm --column scope',
            'zone blacklist list',
            'zone export list',
            'zone import list',
            'zone list',
            'zone transfer accept list',
            'zone transfer request list'
        ]

        # commands
        self.add_cmd_output([
            'openstack %s --all-projects' % sub for sub in subcmds
        ])

        # get recordsets for each zone
        cmd = "openstack zone list -f value -c id"
        ret = self.exec_cmd(cmd)
        if ret['status'] == 0:
            for zone in ret['output'].splitlines():
                zone = zone.split()[0]
                self.add_cmd_output(
                    "openstack recordset list --all-projects %s" % zone,
                    subdir='recordset')

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


class Ubuntudesignate(OpenStackDesignate, UbuntuPlugin):

    packages = ('designate-common',)

# vim: set et ts=4 sw=4 :
