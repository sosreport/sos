# Copyright (C) 2013 Red Hat, Inc.
# Copyright (C) 2017 Red Hat, Inc., Martin Schuppert <mschuppert@redhat.com>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
import os


class OpenStackHeat(Plugin):
    """OpenStack Heat
    """
    plugin_name = "openstack_heat"
    profiles = ('openstack', 'openstack_controller')

    option_list = []
    var_puppet_gen = "/var/lib/config-data/puppet-generated/heat"

    def setup(self):

        # collect commands output only if the openstack-heat-api service
        # is running
        service_status = self.get_command_output(
            "systemctl status openstack-heat-api.service"
        )

        container_status = self.get_command_output("docker ps")
        in_container = False
        if container_status['status'] == 0:
            for line in container_status['output'].splitlines():
                if line.endswith("heat_api"):
                    in_container = True

        if (service_status['status'] == 0) or in_container:
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

        self.limit = self.get_option("log_size")
        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/heat/",
                "/var/log/containers/heat/",
                "/var/log/containers/httpd/heat-api/",
                "/var/log/containers/httpd/heat-api-cfn"
            ], sizelimit=self.limit)
        else:
            self.add_copy_spec([
                "/var/log/heat/*.log",
                "/var/log/containers/heat/*.log",
                "/var/log/containers/httpd/heat-api/*log",
                "/var/log/containers/httpd/heat-api-cfn/*log"
            ], sizelimit=self.limit)

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

        if self.get_option("verify"):
            self.add_cmd_output("rpm -V %s" % ' '.join(self.packages))

    def postproc(self):
        protect_keys = [
            "admin_password", "memcache_secret_key", "password", "connection",
            "qpid_password", "rabbit_password", "stack_domain_admin_password",
        ]

        regexp = r"((?m)^\s*(%s)\s*=\s*)(.*)" % "|".join(protect_keys)
        self.do_path_regex_sub(
            "/etc/heat/*",
            regexp, r"\1*********")
        self.do_path_regex_sub(
            self.var_puppet_gen + "/etc/heat/*",
            regexp, r"\1*********"
        )
        self.do_path_regex_sub(
            self.var_puppet_gen + "_api/etc/heat/*",
            regexp, r"\1*********"
        )
        self.do_path_regex_sub(
            self.var_puppet_gen + "_api_cfn/etc/heat/*",
            regexp, r"\1*********"
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


class RedHatHeat(OpenStackHeat, RedHatPlugin):

    packages = (
        'openstack-heat-api',
        'openstack-heat-api-cfn',
        'openstack-heat-api-cloudwatch',
        'openstack-heat-cli',
        'openstack-heat-common',
        'openstack-heat-engine',
        'python-heatclient'
    )

# vim: set et ts=4 sw=4 :
