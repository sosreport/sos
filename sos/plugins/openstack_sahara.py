# Copyright (C) 2015 Red Hat, Inc.,Poornima M. Kshirsagar <pkshiras@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class OpenStackSahara(Plugin):
    """OpenStack Sahara"""
    plugin_name = 'openstack_sahara'
    profiles = ('openstack', 'openstack_controller')

    option_list = []
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
                "/var/log/containers/sahara/"
            ])
        else:
            self.add_copy_spec([
                "/var/log/sahara/*.log",
                "/var/log/containers/sahara/*.log"
            ])

        if self.get_option("verify"):
            self.add_cmd_output("rpm -V %s" % ' '.join(self.packages))

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
            "xenapi_connection_password"
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
    """OpenStackSahara related information for Debian based distributions."""

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
    """OpenStack sahara related information for Red Hat distributions."""

    packages = (
        'openstack-sahara',
        'openstack-sahara-api',
        'openstack-sahara-engine',
        'python-saharaclient'
    )

    def setup(self):
        super(RedHatSahara, self).setup()
        self.add_copy_spec("/etc/sudoers.d/sahara*")


# vim: et ts=4 sw=4
