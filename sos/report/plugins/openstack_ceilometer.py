# Copyright (C) 2013 Red Hat, Inc., Eoghan Lynn <eglynn@redhat.com>
# Copyright (C) 2012 Rackspace US, Inc.
#               2012 Justin Shepherd <jshepher@rackspace.com>
# Copyright (C) 2009 Red Hat, Inc.
#               2009 Joey Boggs <jboggs@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class OpenStackCeilometer(Plugin):

    short_desc = 'Openstack Ceilometer'
    plugin_name = "openstack_ceilometer"
    profiles = ('openstack', 'openstack_controller', 'openstack_compute')
    var_puppet_gen = "/var/lib/config-data/puppet-generated/ceilometer"

    def setup(self):
        # Ceilometer
        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/ceilometer/*",
            ])
        else:
            self.add_copy_spec([
                "/var/log/ceilometer/*.log",
            ])
        self.add_copy_spec([
            "/etc/ceilometer/*",
            self.var_puppet_gen + "/etc/ceilometer/*"
        ])

    def apply_regex_sub(self, regexp, subst):
        self.do_path_regex_sub("/etc/ceilometer/*", regexp, subst)
        self.do_path_regex_sub(
            self.var_puppet_gen + "/etc/ceilometer/*",
            regexp, subst
        )

    def postproc(self):
        protect_keys = [
            "admin_password", "connection_password", "host_password",
            "memcache_secret_key", "os_password", "password", "qpid_password",
            "rabbit_password", "readonly_user_password", "secret_key",
            "ssl_key_password", "telemetry_secret", "metering_secret"
        ]
        connection_keys = ["connection", "backend_url", "transport_url"]

        self.apply_regex_sub(
            r"((?m)^\s*(%s)\s*=\s*)(.*)" % "|".join(protect_keys),
            r"\1*********"
        )
        self.apply_regex_sub(
            r"((?m)^\s*(%s)\s*=\s*(.*)://(\w*):)(.*)(@(.*))" %
            "|".join(connection_keys),
            r"\1*********\6"
        )


class DebianCeilometer(OpenStackCeilometer, DebianPlugin,
                       UbuntuPlugin):

    packages = (
        'ceilometer-api',
        'ceilometer-agent-central',
        'ceilometer-agent-compute',
        'ceilometer-collector',
        'ceilometer-common',
        'python-ceilometer',
        'python-ceilometerclient'
    )


class RedHatCeilometer(OpenStackCeilometer, RedHatPlugin):

    packages = ('openstack-selinux',)

    def setup(self):
        super(RedHatCeilometer, self).setup()
        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/containers/ceilometer/*",
            ])
        else:
            self.add_copy_spec([
                "/var/log/containers/ceilometer/*.log",
            ])

# vim: set et ts=4 sw=4 :
