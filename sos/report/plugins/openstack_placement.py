# Copyright (C) 2019 Red Hat, Inc., Lee Yarwood <lyarwood@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os
from sos.report.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class OpenStackPlacement(Plugin):

    short_desc = 'OpenStack Placement'
    plugin_name = "openstack_placement"
    profiles = ('openstack', 'openstack_controller')
    containers = ('.*placement_api',)

    var_puppet_gen = "/var/lib/config-data/puppet-generated/placement"
    service_name = 'openstack-placement-api'
    apachepkg = None

    def setup(self):

        # collect commands output only if the openstack-placement-api service
        # is running

        in_container = self.container_exists('.*placement_api')

        if self.is_service_running(self.service_name) or in_container:
            placement_config = ""
            # if containerized we need to pass the config to the cont.
            if in_container:
                placement_config = "--config-dir " + self.var_puppet_gen + \
                                "/etc/placement/"
            self.add_cmd_output(
                "placement-manage " + placement_config + " db version",
                suggest_filename="placement-manage_db_version"
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
                res = self.collect_cmd_output(
                    "openstack resource provider list"
                )

                if res['status'] == 0:
                    resource_provider_list = res['output']
                    for provider in resource_provider_list.splitlines()[3:-1]:
                        res_provider = provider.split()[1]
                        sub_cmds = [
                            "inventory",
                            "trait",
                            "aggregate",
                        ]
                        self.add_cmd_output([
                            f"openstack resource provider {sub_cmd} list "
                            f"{res_provider}"
                            for sub_cmd in sub_cmds
                        ])

        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/placement/",
                "/var/log/containers/placement/",
                "/var/log/containers/httpd/placement-api/",
                f"/var/log/{self.apachepkg}*/placement*",
            ])
        else:
            self.add_copy_spec([
                "/var/log/placement/*.log",
                "/var/log/containers/placement/*.log",
                "/var/log/containers/httpd/placement-api/*log",
                f"/var/log/{self.apachepkg}*/placement*.log",
            ])

        self.add_copy_spec([
            "/etc/placement/",
            self.var_puppet_gen + "/etc/placement/",
            self.var_puppet_gen + "/etc/my.cnf.d/tripleo.cnf",
            self.var_puppet_gen + "/etc/httpd/conf/",
            self.var_puppet_gen + "/etc/httpd/conf.d/",
            self.var_puppet_gen + "/etc/httpd/conf.modules.d/*.conf",
        ])

    def apply_regex_sub(self, regexp, subst):
        """ Apply regex substitution """
        self.do_path_regex_sub("/etc/placement/*", regexp, subst)
        self.do_path_regex_sub(
            self.var_puppet_gen + "/etc/placement/*",
            regexp, subst
        )

    def postproc(self):
        protect_keys = [
            "password",
            "memcache_secret_key",
            "NOVA_API_PASS",
            "PLACEMENT_PASS",
        ]
        connection_keys = [
            "database_connection",
            "slave_connection",
            "connection",
        ]

        join_con_keys = "|".join(connection_keys)

        self.apply_regex_sub(
            fr"(^\s*({'|'.join(protect_keys)})\s*=\s*)(.*)",
            r"\1*********"
        )
        self.apply_regex_sub(
            fr"(^\s*({join_con_keys})\s*=\s*(.*)://(\w*):)(.*)(@(.*))",
            r"\1*********\6"
        )


class DebianPlacement(OpenStackPlacement, DebianPlugin, UbuntuPlugin):

    apachepkg = "apache2"
    packages = (
        'placement-common',
        'placement-api',
        'python3-placement',
    )


class RedHatPlacement(OpenStackPlacement, RedHatPlugin):

    apachepkg = "httpd"
    packages = ('openstack-selinux',)

# vim: set et ts=4 sw=4 :
