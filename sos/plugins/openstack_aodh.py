# Copyright (C) 2017 Red Hat, Inc., Sachin Patil <psachin@redhat.com>
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

import os
from sos.plugins import Plugin, RedHatPlugin


class OpenStackAodh(Plugin, RedHatPlugin):
    """OpenStack Alarm service"""
    plugin_name = "openstack_aodh"
    profiles = ('openstack', 'openstack_controller')

    packages = (
        'openstack-aodh-api',
        'openstack-aodh-listener',
        'openstack-aodh-notifier',
        'openstack-aodh-evaluator,'
        'openstack-aodh-common'
    )

    requires_root = False

    var_puppet_gen = "/var/lib/config-data/puppet-generated/aodh"

    def setup(self):
        self.add_copy_spec([
            "/etc/aodh/",
            self.var_puppet_gen + "/etc/aodh/*",
            self.var_puppet_gen + "/etc/httpd/conf/*",
            self.var_puppet_gen + "/etc/httpd/conf.d/*",
            self.var_puppet_gen + "/etc/httpd/conf.modules.d/wsgi.conf",
            self.var_puppet_gen + "/etc/my.cnf.d/tripleo.cnf"
        ])

        self.limit = self.get_option("log_size")
        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/aodh/*",
                "/var/log/containers/aodh/*",
                "/var/log/containers/httpd/aodh-api/*"
            ], sizelimit=self.limit)
        else:
            self.add_copy_spec([
                "/var/log/aodh/*.log",
                "/var/log/containers/aodh/*.log",
                "/var/log/containers/httpd/aodh-api/*log"
            ], sizelimit=self.limit)

        vars_all = [p in os.environ for p in [
            'OS_USERNAME', 'OS_PASSWORD', 'OS_AUTH_TYPE'
        ]]

        vars_any = [p in os.environ for p in [
            'OS_TENANT_NAME', 'OS_PROJECT_NAME'
        ]]

        if not (all(vars_all) and any(vars_any)):
            self.soslog.warning("Not all environment variables set. Source "
                                "the environment file for the user intended "
                                "to connect to the OpenStack environment.")
        else:
            self.add_cmd_output([
                "aodh --version",
                "aodh capabilities list",
                "aodh alarm list"
            ])

    def postproc(self):
        self.do_file_sub(
            "/etc/aodh/aodh.conf",
            r"(password[\t\ ]*=[\t\ ]*)(.+)",
            r"\1********"
        )

        self.do_file_sub(
            "/etc/aodh/aodh.conf",
            r"(rabbit_password[\t\ ]*=[\t\ ]*)(.+)",
            r"\1********",
        )

        self.do_file_sub(
            self.var_puppet_gen + "/etc/aodh/aodh.conf",
            r"(password[\t\ ]*=[\t\ ]*)(.+)",
            r"\1********"
        )

        self.do_file_sub(
            self.var_puppet_gen + "/etc/aodh/aodh.conf",
            r"(rabbit_password[\t\ ]*=[\t\ ]*)(.+)",
            r"\1********",
        )


# vim: set et ts=4 sw=4 :
