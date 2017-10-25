# Copyright (C) 2009 Red Hat, Inc., Joey Boggs <jboggs@redhat.com>
# Copyright (C) 2012 Rackspace US, Inc.,
#                    Justin Shepherd <jshepher@rackspace.com>
# Copyright (C) 2013 Red Hat, Inc., Jeremy Agee <jagee@redhat.com>

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


class OpenStackHorizon(Plugin):
    """OpenStack Horizon
    """

    plugin_name = "openstack_horizon"
    profiles = ('openstack', 'openstack_controller')
    option_list = []
    var_puppet_gen = "/var/lib/config-data/puppet-generated"

    def setup(self):

        self.limit = self.get_option("log_size")
        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/horizon/",
                "/var/log/containers/horizon/",
                "/var/log/containers/httpd/horizon/"
            ], sizelimit=self.limit)
        else:
            self.add_copy_spec([
                "/var/log/horizon/*.log",
                "/var/log/containers/horizon/*.log",
                "/var/log/containers/httpd/horizon/*log"
            ], sizelimit=self.limit)

        self.add_copy_spec([
            "/etc/openstack-dashboard/",
            self.var_puppet_gen + "/horizon/etc/openstack-dashboard/",
            self.var_puppet_gen + "/horizon/etc/httpd/conf/",
            self.var_puppet_gen + "/horizon/etc/httpd/conf.d/",
            self.var_puppet_gen + "/horizon/etc/httpd/conf.modules.d/*.conf",
            self.var_puppet_gen + "/memcached/etc/sysconfig/memcached"
        ])
        self.add_forbidden_path("*.py[co]")

        if self.get_option("verify"):
            self.add_cmd_output("rpm -V %s" % ' '.join(self.packages))

    def postproc(self):
        var_puppet_gen = self.var_puppet_gen + "/horizon"
        protect_keys = [
            "SECRET_KEY", "EMAIL_HOST_PASSWORD"
        ]

        regexp = r"((?m)^\s*(%s)\s*=\s*)(.*)" % "|".join(protect_keys)
        self.do_path_regex_sub(
            "/etc/openstack-dashboard/.*\.json",
            regexp, r"\1*********"
        )
        self.do_path_regex_sub(
            var_puppet_gen + "/etc/openstack-dashboard/.*\.json",
            regexp, r"\1*********"
        )
        self.do_path_regex_sub(
            "/etc/openstack-dashboard/local_settings/.*\.conf.*",
            regexp, r"\1*********"
        )
        self.do_path_regex_sub(
            var_puppet_gen + "/etc/openstack-dashboard/.*\.conf.*",
            regexp, r"\1*********"
        )


class DebianHorizon(OpenStackHorizon, DebianPlugin):

    packages = (
        'python-django-horizon',
        'openstack-dashboard',
        'openstack-dashboard-apache'
    )

    def setup(self):
        super(DebianHorizon, self).setup()
        self.add_copy_spec("/etc/apache2/sites-available/")


class UbuntuHorizon(OpenStackHorizon, UbuntuPlugin):

    packages = (
        'python-django-horizon',
        'openstack-dashboard',
        'openstack-dashboard-ubuntu-theme'
    )

    def setup(self):
        super(UbuntuHorizon, self).setup()
        self.add_copy_spec("/etc/apache2/conf.d/openstack-dashboard.conf")


class RedHatHorizon(OpenStackHorizon, RedHatPlugin):

    packages = (
        'python-django-horizon',
        'openstack-dashboard'
    )

    def setup(self):
        super(RedHatHorizon, self).setup()
        self.add_copy_spec("/etc/httpd/conf.d/openstack-dashboard.conf")
        if self.get_option("log"):
            self.add_copy_spec("/var/log/httpd/")

# vim: set et ts=4 sw=4 :
