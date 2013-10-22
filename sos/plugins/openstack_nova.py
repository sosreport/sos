## Copyright (C) 2009 Red Hat, Inc., Joey Boggs <jboggs@redhat.com>
## Copyright (C) 2012 Rackspace US, Inc., Justin Shepherd <jshepher@rackspace.com>
## Copyright (C) 2013 Red Hat, Inc., Jeremy Agee <jagee@redhat.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import sos.plugintools

class OpenStackNova(sos.plugintools.PluginBase):
    """openstack nova related information
    """

    optionList = [("log", "gathers openstack nova logs", "slow", True),
                   ("cmds", "gathers openstack nova commands", "slow", False)]

    packages = ('openstack-nova-common',
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
                'novnc')

    def setup(self):
        if self.getOption("cmds"):
            self.collectExtOutput(
                "nova-manage config list 2>/dev/null | sort",
                suggest_filename="nova_config_list")
            self.collectExtOutput(
                "nova-manage service list 2>/dev/null",
                suggest_filename="nova_service_list")
            self.collectExtOutput(
                "nova-manage db version 2>/dev/null",
                suggest_filename="nova_db_version")
            self.collectExtOutput(
                "nova-manage fixed list 2>/dev/null",
                suggest_filename="nova_fixed_ip_list")
            self.collectExtOutput(
                "nova-manage floating list 2>/dev/null",
                suggest_filename="nova_floating_ip_list")
            self.collectExtOutput(
                "nova-manage flavor list 2>/dev/null",
                suggest_filename="nova_flavor_list")
            self.collectExtOutput(
                "nova-manage network list 2>/dev/null",
                suggest_filename="nova_network_list")
            self.collectExtOutput(
                "nova-manage vm list 2>/dev/null",
                suggest_filename="nova_vm_list")

        if self.getOption("log"):
            self.addCopySpec("/var/log/nova/")

        self.addCopySpecs([
                "/etc/logrotate.d/openstack-nova",
                "/etc/polkit-1/localauthority/50-local.d/50-nova.pkla",
                "/etc/sudoers.d/nova",
                "/etc/security/limits.d/91-nova.conf",
                "/etc/sysconfig/openstack-nova-novncproxy",
                "/etc/nova/"
        ])

    def postproc(self):
        protect_keys = [
            "ldap_dns_password", "neutron_admin_password", "rabbit_password",
            "qpid_password", "powervm_mgr_passwd", "virtual_power_host_pass",
            "xenapi_connection_password", "password", "host_password",
            "vnc_password", "connection", "sql_connection", "admin_password"
        ]

        regexp = r"((?m)^\s*#*(%s)\s*=\s*)(.*)" % "|".join(protect_keys)

        for conf_file in ["/etc/nova/nova.conf", "/etc/nova/api-paste.ini"]:
            self.doRegexSub(conf_file, regexp, r"\1*********")


