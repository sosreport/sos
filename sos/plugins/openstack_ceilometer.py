# Copyright (C) 2013 Red Hat, Inc., Eoghan Lynn <eglynn@redhat.com>
# Copyright (C) 2012 Rackspace US, Inc.
#               2012 Justin Shepherd <jshepher@rackspace.com>
# Copyright (C) 2009 Red Hat, Inc.
#               2009 Joey Boggs <jboggs@redhat.com>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class OpenStackCeilometer(Plugin):
    """Openstack Ceilometer"""
    plugin_name = "openstack_ceilometer"
    profiles = ('openstack', 'openstack_controller', 'openstack_compute')

    option_list = []

    def setup(self):
        # Ceilometer
        self.limit = self.get_option("log_size")
        if self.get_option("all_logs"):
            self.add_copy_spec_limit("/var/log/ceilometer/",
                                     sizelimit=self.limit)
        else:
            self.add_copy_spec_limit("/var/log/ceilometer/*.log",
                                     sizelimit=self.limit)
        self.add_copy_spec("/etc/ceilometer/")

    def postproc(self):
        protect_keys = [
            "admin_password", "connection_password", "host_password",
            "memcache_secret_key", "os_password", "password", "qpid_password",
            "rabbit_password", "readonly_user_password", "secret_key",
            "ssl_key_password", "telemetry_secret", "connection",
            "metering_secret"
        ]

        regexp = r"((?m)^\s*(%s)\s*=\s*)(.*)" % "|".join(protect_keys)
        self.do_path_regex_sub("/etc/ceilometer/*", regexp, r"\1*********")


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

    packages = (
        'openstack-ceilometer',
        'openstack-ceilometer-api',
        'openstack-ceilometer-central',
        'openstack-ceilometer-collector',
        'openstack-ceilometer-common',
        'openstack-ceilometer-compute',
        'python-ceilometerclient'
    )

# vim: set et ts=4 sw=4 :
