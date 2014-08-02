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

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class OpenStackNova(Plugin):
    """openstack nova related information
    """
    plugin_name = "openstack-nova"

    option_list = [("log", "gathers openstack nova logs", "slow", True),
                   ("cmds", "gathers openstack nova commands", "slow", False)]

    def setup(self):
        if self.get_option("cmds"):
            self.add_cmd_output(
                "nova-manage config list",
                suggest_filename="nova_config_list")
            self.add_cmd_output(
                "nova-manage service list",
                suggest_filename="nova_service_list")
            self.add_cmd_output(
                "nova-manage db version",
                suggest_filename="nova_db_version")
            self.add_cmd_output(
                "nova-manage fixed list",
                suggest_filename="nova_fixed_ip_list")
            self.add_cmd_output(
                "nova-manage floating list",
                suggest_filename="nova_floating_ip_list")
            self.add_cmd_output(
                "nova-manage flavor list",
                suggest_filename="nova_flavor_list")
            self.add_cmd_output(
                "nova-manage network list",
                suggest_filename="nova_network_list")
            self.add_cmd_output(
                "nova-manage vm list",
                suggest_filename="nova_vm_list")

        if self.get_option("log"):
            self.add_copy_spec("/var/log/nova/")

        self.add_copy_spec("/etc/nova/")

    def postproc(self):
        protect_keys = [
            "ldap_dns_password", "neutron_admin_password", "rabbit_password",
            "qpid_password", "powervm_mgr_passwd", "virtual_power_host_pass",
            "xenapi_connection_password", "password", "host_password",
            "vnc_password", "connection", "sql_connection", "admin_password"
        ]

        regexp = r"((?m)^\s*#*(%s)\s*=\s*)(.*)" % "|".join(protect_keys)

        for conf_file in ["/etc/nova/nova.conf", "/etc/nova/api-paste.ini"]:
            self.do_file_sub(conf_file, regexp, r"\1*********")


class DebianOpenStackNova(OpenStackNova, DebianPlugin, UbuntuPlugin):
    """OpenStack nova related information for Debian based distributions
    """

    nova = False
    packages = (
        'nova-api-ec2',
        'nova-api-metadata',
        'nova-api-os-compute',
        'nova-api-os-volume',
        'nova-common',
        'nova-compute',
        'nova-compute-kvm',
        'nova-compute-lxc',
        'nova-compute-qemu',
        'nova-compute-uml',
        'nova-compute-xcp',
        'nova-compute-xen',
        'nova-xcp-plugins',
        'nova-consoleauth',
        'nova-network',
        'nova-scheduler',
        'nova-volume',
        'novnc',
        'python-nova',
        'python-novaclient',
        'python-novnc'
    )

    def check_enabled(self):
        self.nova = self.is_installed("nova-common")
        return self.nova

    def setup(self):
        super(DebianOpenStackNova, self).setup()
        self.add_copy_specs(["/etc/sudoers.d/nova_sudoers"])


class RedHatOpenStackNova(OpenStackNova, RedHatPlugin):
    """OpenStack nova related information for Red Hat distributions
    """

    nova = False
    packages = (
        'openstack-nova-common',
        'openstack-nova-network',
        'openstack-nova-conductor',
        'openstack-nova-conductor',
        'openstack-nova-scheduler',
        'openstack-nova-console',
        'openstack-nova-novncproxy',
        'openstack-nova-compute',
        'openstack-nova-api',
        'openstack-nova-cert',
        'openstack-nova-cells',
        'openstack-nova-objectstore',
        'python-nova',
        'python-novaclient',
        'novnc'
    )

    def check_enabled(self):
        self.nova = self.is_installed("openstack-nova-common")
        return self.nova

    def setup(self):
        super(RedHatOpenStackNova, self).setup()
        self.add_copy_specs([
            "/etc/logrotate.d/openstack-nova",
            "/etc/polkit-1/localauthority/50-local.d/50-nova.pkla",
            "/etc/sudoers.d/nova",
            "/etc/security/limits.d/91-nova.conf",
            "/etc/sysconfig/openstack-nova-novncproxy"
        ])

# vim: et ts=4 sw=4
