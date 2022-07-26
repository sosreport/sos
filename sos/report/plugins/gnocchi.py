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
from sos.report.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Gnocchi(Plugin):

    short_desc = 'Gnocchi - Metric as a service'
    plugin_name = "gnocchi"

    profiles = ('openstack', 'openstack_controller')

    def setup(self):
        self.add_copy_spec([
            "/etc/gnocchi/*",
        ])

        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/gnocchi/*",
                "/var/log/{}*/gnocchi*".format(self.apachepkg)
            ])
        else:
            self.add_copy_spec([
                "/var/log/gnocchi/*.log",
                "/var/log/{}*/gnocchi*.log".format(self.apachepkg)
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
            r"ceph_secret\s?=(.*)",
            r"ceph_secret=*****",
        )
        self.do_file_sub(
            "/etc/gnocchi/gnocchi.conf",
            r"password\s?=(.*)",
            r"password=*****",
        )
        self.do_file_sub(
            "/etc/gnocchi/gnocchi.conf",
            r"memcache_secret_key\s?=(.*)",
            r"memcache_secret_key=*****",
        )


class RedHatGnocchi(Gnocchi, RedHatPlugin):

    apachepkg = 'httpd'
    var_puppet_gen = "/var/lib/config-data/puppet-generated/gnocchi"

    packages = (
        'openstack-gnocchi-metricd', 'openstack-gnocchi-common',
        'openstack-gnocchi-statsd', 'openstack-gnocchi-api',
        'openstack-gnocchi-carbonara'
    )

    def setup(self):
        super(RedHatGnocchi, self).setup()
        self.add_copy_spec([
            self.var_puppet_gen + "/etc/gnocchi/*",
            self.var_puppet_gen + "/etc/httpd/conf/*",
            self.var_puppet_gen + "/etc/httpd/conf.d/*",
            self.var_puppet_gen + "/etc/httpd/conf.modules.d/wsgi.conf",
            self.var_puppet_gen + "/etc/my.cnf.d/tripleo.cnf"
        ])

    def postproc(self):
        super(RedHatGnocchi, self).postproc()
        self.do_file_sub(
            self.var_puppet_gen + "/etc/gnocchi/"
            "gnocchi.conf",
            r"password=(.*)",
            r"password=*****",
        )


class DebianGnocchi(Gnocchi, DebianPlugin, UbuntuPlugin):

    apachepkg = 'apache'

    packages = (
        'gnocchi-api', 'gnocchi-metricd', 'gnocchi-common'
        'gnocchi-statsd', 'python3-gnocchiclient'
    )

# vim: set et ts=4 sw=4 :
