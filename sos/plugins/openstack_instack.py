# Copyright (C) 2015 Red Hat, Inc., Lee Yarwood <lyarwood@redhat.com>

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

from sos.plugins import Plugin, RedHatPlugin


class OpenStackInstack(Plugin):
    """OpenStack Instack
    """
    plugin_name = "openstack_instack"
    profiles = ('openstack', 'openstack_undercloud')

    def setup(self):
        self.add_copy_spec("/home/stack/.instack/install-undercloud.log")
        self.add_copy_spec("/home/stack/instackenv.json")
        self.add_copy_spec("/home/stack/undercloud.conf")

    def postproc(self):
        protected_keys = [
            "UNDERCLOUD_TUSKAR_PASSWORD", "UNDERCLOUD_ADMIN_PASSWORD",
            "UNDERCLOUD_CEILOMETER_METERING_SECRET",
            "UNDERCLOUD_CEILOMETER_PASSWORD",
            "UNDERCLOUD_CEILOMETER_SNMPD_PASSWORD",
            "UNDERCLOUD_DB_PASSWORD", "UNDERCLOUD_GLANCE_PASSWORD",
            "UNDERCLOUD_HEAT_PASSWORD",
            "UNDERCLOUD_HEAT_STACK_DOMAIN_ADMIN_PASSWORD",
            "UNDERCLOUD_HORIZON_SECRET_KEY", "UNDERCLOUD_IRONIC_PASSWORD",
            "UNDERCLOUD_NEUTRON_PASSWORD", "UNDERCLOUD_NOVA_PASSWORD",
            "UNDERCLOUD_RABBIT_PASSWORD", "UNDERCLOUD_SWIFT_PASSWORD",
            "UNDERCLOUD_TUSKAR_PASSWORD", "OS_PASSWORD",
            "undercloud_db_password", "undercloud_admin_password",
            "undercloud_glance_password", "undercloud_heat_password",
            "undercloud_neutron_password", "undercloud_nova_password",
            "undercloud_ironic_password", "undercloud_tuskar_password",
            "undercloud_ceilometer_password",
            "undercloud_ceilometer_metering_secret",
            "undercloud_ceilometer_snmpd_password",
            "undercloud_swift_password", "undercloud_rabbit_password",
            "undercloud_heat_stack_domain_admin_password"
        ]
        regexp = r"((?m)(%s)=)(.*)" % "|".join(protected_keys)
        self.do_file_sub("/home/stack/.instack/install-undercloud.log",
                         regexp, r"\1*********")
        self.do_file_sub("/home/stack/undercloud.conf", regexp, r"\1*********")

        protected_json_keys = ["pm_password", "ssh-key", "password"]
        json_regexp = r'((?m)"(%s)": )(".*?")' % "|".join(protected_json_keys)
        self.do_file_sub("/home/stack/instackenv.json", json_regexp,
                         r"\1*********")


class RedHatRDOManager(OpenStackInstack, RedHatPlugin):

    packages = [
        'instack',
        'instack-undercloud',
    ]

    def setup(self):
        super(RedHatRDOManager, self).setup()

# vim: set et ts=4 sw=4 :
