# Copyright (C) 2013 Red Hat, Inc., Flavio Percoco <fpercoco@redhat.com>
# Copyright (C) 2012 Rackspace US, Inc.,
#                    Justin Shepherd <jshepher@rackspace.com>
# Copyright (C) 2009 Red Hat, Inc., Joey Boggs <jboggs@redhat.com>
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


class OpenStackGlance(Plugin):
    """OpenStack Glance"""
    plugin_name = "openstack_glance"
    profiles = ('openstack', 'openstack_controller')

    option_list = []
    var_puppet_gen = "/var/lib/config-data/puppet-generated/glance_api"

    def setup(self):
        self.limit = self.get_option("log_size")
        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/glance/",
                "/var/log/containers/glance/",
                "/var/log/containers/httpd/glance-api/"
            ], sizelimit=self.limit)
        else:
            self.add_copy_spec([
                "/var/log/glance/*.log",
                "/var/log/containers/glance/*.log",
                "/var/log/containers/httpd/glance-api/*log"
            ], sizelimit=self.limit)

        self.add_copy_spec([
            "/etc/glance/",
            self.var_puppet_gen + "/etc/glance/",
            self.var_puppet_gen + "/etc/my.cnf.d/tripleo.cnf"
        ])

        if self.get_option("verify"):
            self.add_cmd_output("rpm -V %s" % ' '.join(self.packages))

        # collect commands output only if the openstack-glance-api service
        # is running
        service_status = self.get_command_output(
            "systemctl status openstack-glance-api.service"
        )

        container_status = self.get_command_output("docker ps")
        in_container = False
        if container_status['status'] == 0:
            for line in container_status['output'].splitlines():
                if line.endswith("glance_api"):
                    in_container = True

        if (service_status['status'] == 0) or in_container:
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

    def postproc(self):
        protect_keys = [
            "admin_password", "password", "qpid_password", "rabbit_password",
            "s3_store_secret_key", "ssl_key_password", "connection",
            "vmware_server_password"
        ]

        regexp = r"((?m)^\s*(%s)\s*=\s*)(.*)" % "|".join(protect_keys)
        self.do_path_regex_sub("/etc/glance/*", regexp, r"\1*********")
        self.do_path_regex_sub(
            self.var_puppet_gen + "/etc/glance/*",
            regexp, r"\1*********"
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


class RedHatGlance(OpenStackGlance, RedHatPlugin):

    packages = (
        'openstack-glance',
        'python-glanceclient'
    )

# vim: set et ts=4 sw=4 :
