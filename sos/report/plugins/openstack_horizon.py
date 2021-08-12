# Copyright (C) 2009 Red Hat, Inc., Joey Boggs <jboggs@redhat.com>
# Copyright (C) 2012 Rackspace US, Inc.,
#                    Justin Shepherd <jshepher@rackspace.com>
# Copyright (C) 2013 Red Hat, Inc., Jeremy Agee <jagee@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class OpenStackHorizon(Plugin):

    short_desc = 'OpenStack Horizon'

    plugin_name = "openstack_horizon"
    profiles = ('openstack', 'openstack_controller')
    var_puppet_gen = "/var/lib/config-data/puppet-generated"

    def setup(self):
        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/horizon/",
            ])
        else:
            self.add_copy_spec([
                "/var/log/horizon/*.log",
            ])

        self.add_copy_spec([
            "/etc/openstack-dashboard/",
            self.var_puppet_gen + "/horizon/etc/openstack-dashboard/",
            self.var_puppet_gen + "/horizon/etc/httpd/conf/",
            self.var_puppet_gen + "/horizon/etc/httpd/conf.d/",
            self.var_puppet_gen + "/horizon/etc/httpd/conf.modules.d/*.conf",
            self.var_puppet_gen + "/memcached/etc/sysconfig/memcached"
        ])
        self.add_forbidden_path(
            "/etc/openstack-dashboard/local_settings.d/*.py[co]"
        )

    def postproc(self):
        var_puppet_gen = self.var_puppet_gen + "/horizon"
        protect_keys = [
            "SECRET_KEY", "EMAIL_HOST_PASSWORD"
        ]

        regexp = r"((?m)^\s*(%s)\s*=\s*)(.*)" % "|".join(protect_keys)
        self.do_path_regex_sub(
            r"/etc/openstack-dashboard/.*\.json",
            regexp, r"\1*********"
        )
        self.do_path_regex_sub(
            var_puppet_gen + r"/etc/openstack-dashboard/.*\.json",
            regexp, r"\1*********"
        )
        self.do_path_regex_sub(
            "/etc/openstack-dashboard/local_settings$",
            regexp, r"\1*********"
        )
        self.do_path_regex_sub(
            var_puppet_gen + "/etc/openstack-dashboard/local_settings$",
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

    packages = ('openstack-selinux',)

    def setup(self):
        super(RedHatHorizon, self).setup()
        self.add_copy_spec("/etc/httpd/conf.d/openstack-dashboard.conf")
        if self.get_option("all_logs"):
            self.add_copy_spec("/var/log/httpd/horizon*")
        else:
            self.add_copy_spec([
                "/var/log/httpd/horizon*.log"
                "/var/log/httpd/"
            ])

# vim: set et ts=4 sw=4 :
