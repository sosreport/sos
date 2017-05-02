# Copyright (C) 2009 Red Hat, Inc., Joey Boggs <jboggs@redhat.com>
# Copyright (C) 2012 Rackspace US, Inc.,
#                    Justin Shepherd <jshepher@rackspace.com>
# Copyright (C) 2013 Red Hat, Inc., Jeremy Agee <jagee@redhat.com>
# Copyright (C) 2015 Red Hat, Inc., Abhijeet Kasurde <akasurde@redhat.com>
# Copyright (C) 2017 Red Hat, Inc., Martin Schuppert <mschuppert@redhat.com>

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
import os


class OpenStackNova(Plugin):
    """OpenStack Nova
    """
    plugin_name = "openstack_nova"
    profiles = ('openstack', 'openstack_controller', 'openstack_compute')

    def setup(self):
        # commands we do not need to source the environment file
        self.add_cmd_output("nova-manage db version")
        self.add_cmd_output("nova-manage fixed list")
        self.add_cmd_output("nova-manage floating list")

        vars = [p in os.environ for p in [
                'OS_USERNAME', 'OS_PASSWORD', 'OS_TENANT_NAME']]
        if not all(vars):
            self.soslog.warning("Not all environment variables set. Source "
                                "the environment file for the user intended "
                                "to connect to the OpenStack environment.")
        else:
            self.add_cmd_output("nova service-list")
            self.add_cmd_output("openstack flavor list --long")
            self.add_cmd_output("nova network-list")
            self.add_cmd_output("nova list")
            self.add_cmd_output("nova agent-list")
            self.add_cmd_output("nova version-list")
            self.add_cmd_output("nova host-list")
            self.add_cmd_output("openstack quota show")
            self.add_cmd_output("openstack hypervisor stats show")
            # get details for each nova instance
            cmd = "openstack server list -f value"
            nova_instances = self.call_ext_prog(cmd)['output']
            for instance in nova_instances.splitlines():
                instance = instance.split()[0]
                cmd = "openstack server show %s" % (instance)
                self.add_cmd_output(
                    cmd,
                    suggest_filename="instance-" + instance + ".log")

        self.limit = self.get_option("log_size")
        if self.get_option("all_logs"):
            self.add_copy_spec("/var/log/nova/", sizelimit=self.limit)
        else:
            self.add_copy_spec("/var/log/nova/*.log", sizelimit=self.limit)

        self.add_copy_spec("/etc/nova/")

        if self.get_option("verify"):
            self.add_cmd_output("rpm -V %s" % ' '.join(self.packages))

    def postproc(self):
        protect_keys = [
            "ldap_dns_password", "neutron_admin_password", "rabbit_password",
            "qpid_password", "powervm_mgr_passwd", "virtual_power_host_pass",
            "xenapi_connection_password", "password", "host_password",
            "vnc_password", "connection", "sql_connection", "admin_password",
            "connection_password", "memcache_secret_key", "s3_secret_key",
            "metadata_proxy_shared_secret"
        ]

        regexp = r"((?m)^\s*(%s)\s*=\s*)(.*)" % "|".join(protect_keys)
        self.do_path_regex_sub("/etc/nova/*", regexp, r"\1*********")


class DebianNova(OpenStackNova, DebianPlugin, UbuntuPlugin):

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
        super(DebianNova, self).setup()
        self.add_copy_spec([
            "/etc/sudoers.d/nova_sudoers",
            "/usr/share/polkit-1/rules.d/60-libvirt.rules",
        ])


class RedHatNova(OpenStackNova, RedHatPlugin):

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
        super(RedHatNova, self).setup()
        self.add_copy_spec([
            "/etc/logrotate.d/openstack-nova",
            "/etc/polkit-1/localauthority/50-local.d/50-nova.pkla",
            "/etc/sudoers.d/nova",
            "/etc/security/limits.d/91-nova.conf",
            "/etc/sysconfig/openstack-nova-novncproxy"
        ])

# vim: set et ts=4 sw=4 :
