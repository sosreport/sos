# Copyright (C) 2013 Red Hat, Inc., Flavio Percoco <fpercoco@redhat.com>
# Copyright (C) 2012 Rackspace US, Inc.,
#                    Justin Shepherd <jshepher@rackspace.com>
# Copyright (C) 2009 Red Hat, Inc., Joey Boggs <jboggs@redhat.com>
# Copyright (C) 2017 Red Hat, Inc., Martin Schuppert <mschuppert@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
import os


class OpenStackGlance(Plugin):

    short_desc = 'OpenStack Glance'
    plugin_name = "openstack_glance"
    profiles = ('openstack', 'openstack_controller')
    containers = ('glance_api',)

    var_puppet_gen = "/var/lib/config-data/puppet-generated/glance_api"
    service_name = "openstack-glance-api.service"

    def setup(self):
        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/glance/",
            ])
        else:
            self.add_copy_spec([
                "/var/log/glance/*.log",
            ])

        self.add_copy_spec([
            "/etc/glance/",
            self.var_puppet_gen + "/etc/glance/",
            self.var_puppet_gen + "/etc/my.cnf.d/tripleo.cnf"
        ])

        # collect commands output only if the openstack-glance-api service
        # is running
        in_container = self.container_exists('glance_api')

        if self.is_service_running(self.service_name) or in_container:
            glance_config = ""
            # if containerized we need to pass the config to the cont.
            if in_container:
                glance_config = "--config-dir " + self.var_puppet_gen + \
                                "/etc/glance/"

            self.add_cmd_output(
                "glance-manage " + glance_config + " db_version",
                suggest_filename="glance_db_version"
            )

            vars_all = [p in os.environ for p in [
                        'OS_USERNAME', 'OS_PASSWORD']]

            vars_any = [p in os.environ for p in [
                        'OS_TENANT_NAME', 'OS_PROJECT_NAME']]

            if not (all(vars_all) and any(vars_any)):
                self.soslog.warning("Not all environment variables set. "
                                    "Source the environment file for the user "
                                    "intended to connect to the OpenStack "
                                    "environment.")
            else:
                self.add_cmd_output("openstack image list --long")

    def apply_regex_sub(self, regexp, subst):
        self.do_path_regex_sub("/etc/glance/*", regexp, subst)
        self.do_path_regex_sub(
            self.var_puppet_gen + "/etc/glance/*",
            regexp, subst
        )

    def postproc(self):
        protect_keys = [
            "admin_password", "password", "qpid_password", "rabbit_password",
            "s3_store_secret_key", "ssl_key_password",
            "vmware_server_password", "transport_url",
            "memcache_secret_key"
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


class DebianGlance(OpenStackGlance, DebianPlugin, UbuntuPlugin):

    packages = (
        'glance',
        'glance-api',
        'glance-client',
        'glance-common',
        'glance-registry',
        'python-glance'
    )
    service_name = 'glance-api.service'


class RedHatGlance(OpenStackGlance, RedHatPlugin):

    packages = ('openstack-selinux',)

# vim: set et ts=4 sw=4 :
