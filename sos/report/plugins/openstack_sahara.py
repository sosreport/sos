# Copyright (C) 2015 Red Hat, Inc.,Poornima M. Kshirsagar <pkshiras@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class OpenStackSahara(Plugin):

    short_desc = 'OpenStack Sahara'
    plugin_name = 'openstack_sahara'
    profiles = ('openstack', 'openstack_controller')
    var_puppet_gen = "/var/lib/config-data/puppet-generated/sahara"

    def setup(self):
        self.add_copy_spec([
            "/etc/sahara/",
            self.var_puppet_gen + "/etc/sahara/"
        ])
        self.add_journal(units="openstack-sahara-all")
        self.add_journal(units="openstack-sahara-api")
        self.add_journal(units="openstack-sahara-engine")

        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/sahara/",
            ])
        else:
            self.add_copy_spec([
                "/var/log/sahara/*.log",
            ])

    def apply_regex_sub(self, regexp, subst):
        self.do_path_regex_sub("/etc/sahara/*", regexp, subst)
        self.do_path_regex_sub(
            self.var_puppet_gen + "/etc/sahara/*",
            regexp, subst
        )

    def postproc(self):
        protect_keys = [
            "admin_password", "memcache_secret_key", "password",
            "qpid_password", "rabbit_password", "ssl_key_password",
            "xenapi_connection_password", "transport_url"
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


class DebianSahara(OpenStackSahara, DebianPlugin, UbuntuPlugin):

    short_desc = 'OpenStack Sahara information for Debian based distributions'
    packages = (
        'sahara-api',
        'sahara-common',
        'sahara-engine',
        'python-sahara',
        'python-saharaclient',
    )

    def setup(self):
        super(DebianSahara, self).setup()


class RedHatSahara(OpenStackSahara, RedHatPlugin):

    short_desc = 'OpenStack Sahara information for Red Hat distributions'
    packages = ('openstack-selinux',)

    def setup(self):
        super(RedHatSahara, self).setup()
        self.add_copy_spec("/etc/sudoers.d/sahara*")


# vim: et ts=4 sw=4
