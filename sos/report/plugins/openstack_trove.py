# Copyright (C) 2015 Red Hat, Inc., Lee Yarwood <lyarwood@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.


from sos.report.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class OpenStackTrove(Plugin):

    short_desc = 'OpenStack Trove'

    plugin_name = "openstack_trove"
    profiles = ('openstack', 'openstack_controller')
    var_puppet_gen = "/var/lib/config-data/puppet-generated/trove"

    def setup(self):
        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/trove/",
            ])
        else:
            self.add_copy_spec([
                "/var/log/trove/*.log",
            ])

        self.add_copy_spec([
            '/etc/trove/',
            self.var_puppet_gen + '/etc/trove/'
        ])

    def apply_regex_sub(self, regexp, subst):
        self.do_path_regex_sub("/etc/trove/*", regexp, subst)
        self.do_path_regex_sub(
            self.var_puppet_gen + "/etc/trove/*",
            regexp, subst
        )

    def postproc(self):
        protect_keys = [
            "default_password_length", "notifier_queue_password",
            "rabbit_password", "replication_password", "admin_password",
            "dns_passkey", "transport_url", "memcache_secret_key"
        ]
        connection_keys = ["connection"]

        self.apply_regex_sub(
            r"((?m)^\s*(%s)\s*=\s*)(.*)" % "|".join(protect_keys),
            r"\1*********"
        )
        self.apply_regex_sub(
            r"((?m)^\s*(%s)\s*=\s*(.*)://(\w*):)(.*)(@(.*))" %
            "|".join(connection_keys),
            r"\1*********\6"
        )


class DebianTrove(OpenStackTrove, DebianPlugin, UbuntuPlugin):

    packages = (
        'python-trove',
        'trove-common',
        'trove-api',
        'trove-taskmanager'
    )

    def setup(self):
        super(DebianTrove, self).setup()


class RedHatTrove(OpenStackTrove, RedHatPlugin):

    packages = ('openstack-selinux',)

    def setup(self):
        super(RedHatTrove, self).setup()

# vim: set et ts=4 sw=4 :
