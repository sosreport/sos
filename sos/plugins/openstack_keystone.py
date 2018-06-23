# Copyright (C) 2013 Red Hat, Inc., Jeremy Agee <jagee@redhat.com>
# Copyright (C) 2017 Red Hat, Inc., Martin Schuppert <mschuppert@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
import os


class OpenStackKeystone(Plugin):
    """OpenStack Keystone
    """
    plugin_name = "openstack_keystone"
    profiles = ('openstack', 'openstack_controller')

    option_list = [("nopw", "dont gathers keystone passwords", "slow", True)]
    var_puppet_gen = "/var/lib/config-data/puppet-generated/keystone"

    def setup(self):
        self.add_copy_spec([
            "/etc/keystone/default_catalog.templates",
            "/etc/keystone/keystone.conf",
            "/etc/keystone/logging.conf",
            "/etc/keystone/policy.json",
            self.var_puppet_gen + "/etc/keystone/*.conf",
            self.var_puppet_gen + "/etc/keystone/*.json",
            self.var_puppet_gen + "/etc/httpd/conf/",
            self.var_puppet_gen + "/etc/httpd/conf.d/",
            self.var_puppet_gen + "/etc/httpd/conf.modules.d/*.conf",
            self.var_puppet_gen + "/var/spool/cron/",
            self.var_puppet_gen + "/etc/my.cnf.d/tripleo.cnf"
        ])

        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/keystone/",
                "/var/log/containers/keystone/",
                "/var/log/containers/httpd/keystone/"
            ])
        else:
            self.add_copy_spec([
                "/var/log/keystone/*.log",
                "/var/log/containers/keystone/*.log",
                "/var/log/containers/httpd/keystone/*log"
            ])

        # collect domain config directory, if specified
        # if not, collect default /etc/keystone/domains
        self.domain_config_dir = self.get_cmd_output_now(
                "crudini --get /etc/keystone/keystone.conf "
                "identity domain_config_dir")
        if self.domain_config_dir is None or \
                not(os.path.isdir(self.domain_config_dir)):
            self.domain_config_dir = "/etc/keystone/domains"
        self.add_copy_spec(self.domain_config_dir)

        if self.get_option("verify"):
            self.add_cmd_output("rpm -V %s" % ' '.join(self.packages))

        vars_all = [p in os.environ for p in [
                    'OS_USERNAME', 'OS_PASSWORD']]

        vars_any = [p in os.environ for p in [
                    'OS_TENANT_NAME', 'OS_PROJECT_NAME']]

        if not (all(vars_all) and any(vars_any)):
            self.soslog.warning("Not all environment variables set. Source "
                                "the environment file for the user intended "
                                "to connect to the OpenStack environment.")
        else:
            self.add_cmd_output("openstack endpoint list")
            self.add_cmd_output("openstack catalog list")

    def apply_regex_sub(self, regexp, subst):
        self.do_path_regex_sub("/etc/keystone/*", regexp, subst)
        self.do_path_regex_sub(
            self.var_puppet_gen + "/etc/keystone/*",
            regexp, subst
        )

    def postproc(self):
        protect_keys = [
            "password", "qpid_password", "rabbit_password", "ssl_key_password",
            "ldap_dns_password", "neutron_admin_password", "host_password",
            "admin_password", "admin_token", "ca_password"
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

        # obfuscate LDAP plaintext passwords in domain config dir
        self.do_path_regex_sub(self.domain_config_dir,
                               r"((?m)^\s*(%s)\s*=\s*)(.*)", r"\1********")


class DebianKeystone(OpenStackKeystone, DebianPlugin, UbuntuPlugin):

    packages = (
        'keystone',
        'python-keystone',
        'python-keystoneclient'
    )


class RedHatKeystone(OpenStackKeystone, RedHatPlugin):

    packages = (
        'openstack-keystone',
        'python-keystone',
        'python-django-openstack-auth',
        'python-keystoneclient'
    )

    def setup(self):
        super(RedHatKeystone, self).setup()
        if self.get_option("all_logs"):
            self.add_copy_spec("/var/log/httpd/keystone*")
        else:
            self.add_copy_spec("/var/log/httpd/keystone*.log")


# vim: set et ts=4 sw=4 :
