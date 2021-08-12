# Copyright (C) 2013 Red Hat, Inc.
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


class OpenStackHeat(Plugin):

    short_desc = 'OpenStack Heat'
    plugin_name = "openstack_heat"
    profiles = ('openstack', 'openstack_controller')
    containers = ('.*heat_api',)
    var_puppet_gen = "/var/lib/config-data/puppet-generated/heat"
    service_name = "openstack-heat-api.service"

    def setup(self):

        # collect commands output only if the openstack-heat-api service
        # is running
        in_container = self.container_exists('.*heat_api')

        if self.is_service_running(self.service_name) or in_container:
            heat_config = ""
            # if containerized we need to pass the config to the cont.
            if in_container:
                heat_config = "--config-dir " + self.var_puppet_gen + \
                                "_api/etc/heat/"

            self.add_cmd_output(
                "heat-manage " + heat_config + " db_version",
                suggest_filename="heat_db_version"
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
                self.add_cmd_output("openstack stack list")

        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/heat/",
            ])
        else:
            self.add_copy_spec([
                "/var/log/heat/*.log",
            ])

        self.add_copy_spec([
            "/etc/heat/",
            self.var_puppet_gen + "/etc/heat/",
            self.var_puppet_gen + "/etc/my.cnf.d/tripleo.cnf",
            self.var_puppet_gen + "_api/etc/heat/",
            self.var_puppet_gen + "_api/etc/httpd/conf/",
            self.var_puppet_gen + "_api/etc/httpd/conf.d/",
            self.var_puppet_gen + "_api/etc/httpd/conf.modules.d/*.conf",
            self.var_puppet_gen + "_api/var/spool/cron/heat",
            self.var_puppet_gen + "_api_cfn/etc/heat/",
            self.var_puppet_gen + "_api_cfn/etc/httpd/conf/",
            self.var_puppet_gen + "_api_cfn/etc/httpd/conf.d/",
            self.var_puppet_gen + "_api_cfn/etc/httpd/conf.modules.d/*.conf",
            self.var_puppet_gen + "_api_cfn/var/spool/cron/heat",
        ])

    def apply_regex_sub(self, regexp, subst):
        self.do_path_regex_sub(
            "/etc/heat/*",
            regexp, subst)
        self.do_path_regex_sub(
            self.var_puppet_gen + "/etc/heat/*",
            regexp, subst
        )
        self.do_path_regex_sub(
            self.var_puppet_gen + "_api/etc/heat/*",
            regexp, subst
        )
        self.do_path_regex_sub(
            self.var_puppet_gen + "_api_cfn/etc/heat/*",
            regexp, subst
        )

    def postproc(self):
        protect_keys = [
            "admin_password", "memcache_secret_key", "password",
            "qpid_password", "rabbit_password", "stack_domain_admin_password",
            "transport_url"
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


class DebianHeat(OpenStackHeat, DebianPlugin, UbuntuPlugin):

    packages = (
        'heat-api',
        'heat-api-cfn',
        'heat-api-cloudwatch',
        'heat-common',
        'heat-engine',
        'python-heat',
        'python-heatclient'
    )
    service_name = 'heat-api.service'


class RedHatHeat(OpenStackHeat, RedHatPlugin):

    packages = ('openstack-selinux',)

# vim: set et ts=4 sw=4 :
