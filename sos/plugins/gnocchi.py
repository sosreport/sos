# Copyright (C) 2016 Red Hat, Inc., Sachin Patil <psachin@redhat.com>
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


class GnocchiPlugin(Plugin, RedHatPlugin):
    """Gnocchi - Metric as a service"""
    plugin_name = "gnocchi"

    profiles = ('openstack', 'openstack_controller')

    packages = (
        'openstack-gnocchi-metricd', 'openstack-gnocchi-common',
        'openstack-gnocchi-statsd', 'openstack-gnocchi-api',
        'openstack-gnocchi-carbonara'
    )

    requires_root = False

    def setup(self):
        self.add_copy_spec("/etc/gnocchi/")

        self.limit = self.get_option("log_size")
        if self.get_option("all_logs"):
            self.add_copy_spec("/var/log/gnocchi/",
                               sizelimit=self.limit)
        else:
            self.add_copy_spec("/var/log/gnocchi/*.log",
                               sizelimit=self.limit)

        vars = [p in os.environ for p in [
                'OS_USERNAME', 'OS_PASSWORD', 'OS_TENANT_NAME']]
        if not all(vars):
            self.soslog.warning("Not all environment variables set. Source "
                                "the environment file for the user intended "
                                "to connect to the OpenStack environment.")
        else:
            self.add_cmd_output([
                "gnocchi --version",
                "gnocchi status",
                "gnocchi capabilities list",
                "gnocchi archive-policy list",
                "gnocchi resource list",
                "gnocchi resource-type list"
            ])

    def postproc(self):
        self.do_file_sub(
            "/etc/gnocchi/gnocchi.conf",
            r"password=(.*)",
            r"password=*****",
        )

# vim: set et ts=4 sw=4 :
