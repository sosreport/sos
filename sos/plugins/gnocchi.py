# Copyright (C) 2016 Red Hat, Inc., Sachin Patil <psachin@redhat.com>
# Copyright (C) 2017 Red Hat, Inc., Martin Schuppert <mschuppert@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

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

    var_puppet_gen = "/var/lib/config-data/puppet-generated/gnocchi"

    def setup(self):
        self.add_copy_spec([
            "/etc/gnocchi/*",
            self.var_puppet_gen + "/etc/gnocchi/*",
            self.var_puppet_gen + "/etc/httpd/conf/*",
            self.var_puppet_gen + "/etc/httpd/conf.d/*",
            self.var_puppet_gen + "/etc/httpd/conf.modules.d/wsgi.conf",
            self.var_puppet_gen + "/etc/my.cnf.d/tripleo.cnf"
        ])

        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/gnocchi/*",
                "/var/log/httpd/gnocchi*",
                "/var/log/containers/gnocchi/*",
                "/var/log/containers/httpd/gnocchi-api/*"
            ])
        else:
            self.add_copy_spec([
                "/var/log/gnocchi/*.log",
                "/var/log/httpd/gnocchi*.log",
                "/var/log/containers/gnocchi/*.log",
                "/var/log/containers/httpd/gnocchi-api/*log"
            ])

        vars_all = [p in os.environ for p in [
                    'OS_USERNAME', 'OS_PASSWORD']]

        vars_any = [p in os.environ for p in [
                    'OS_TENANT_NAME', 'OS_PROJECT_NAME']]

        if not (all(vars_all) and any(vars_any)):
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
        self.do_file_sub(
            self.var_puppet_gen + "/etc/gnocchi/"
            "gnocchi.conf",
            r"password=(.*)",
            r"password=*****",
        )


# vim: set et ts=4 sw=4 :
