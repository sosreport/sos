# Copyright (C) 2009 Red Hat, Inc., Joey Boggs <jboggs@redhat.com>
# Copyright (C) 2012 Rackspace US, Inc.,
#                    Justin Shepherd <jshepher@rackspace.com>
# Copyright (C) 2013 Red Hat, Inc., Jeremy Agee <jagee@redhat.com>
# Copyright (C) 2015 Red Hat, Inc., Abhijeet Kasurde <akasurde@redhat.com>
# Copyright (C) 2017 Red Hat, Inc., Martin Schuppert <mschuppert@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
import os
import re


class OpenStackNova(Plugin):

    short_desc = 'OpenStack Nova'
    plugin_name = "openstack_nova"
    profiles = ('openstack', 'openstack_controller', 'openstack_compute')
    containers = ('.*nova_api',)

    var_puppet_gen = "/var/lib/config-data/puppet-generated/nova"
    service_name = "openstack-nova-api.service"

    def setup(self):

        # collect commands output only if the openstack-nova-api service
        # is running
        in_container = self.container_exists('.*nova_api')

        if self.is_service_running(self.service_name) or in_container:
            nova_config = ""
            # if containerized we need to pass the config to the cont.
            if in_container:
                nova_config = "--config-dir " + self.var_puppet_gen + \
                                "/etc/nova/"

            self.add_cmd_output(
                "nova-manage " + nova_config + " db version",
                suggest_filename="nova-manage_db_version"
            )
            self.add_cmd_output(
                "nova-manage " + nova_config + " fixed list",
                suggest_filename="nova-manage_fixed_list"
            )
            self.add_cmd_output(
                "nova-manage " + nova_config + " floating list",
                suggest_filename="nova-manage_floating_list"
            )
            self.add_cmd_output(
                "nova-status " + nova_config + " upgrade check",
                suggest_filename="nova-status_upgrade_check"
            )

            vars_all = [p in os.environ for p in [
                        'OS_USERNAME', 'OS_PASSWORD']]

            vars_any = [p in os.environ for p in [
                        'OS_TENANT_NAME', 'OS_PROJECT_NAME']]

            if not (all(vars_all) and any(vars_any)):
                self.soslog.warning("Not all environment variables set. "
                                    "Source the environment file for the user "
                                    "intended to connect to the OpenStack "
                                    "environment.")
            else:
                self.add_cmd_output("nova service-list")
                self.add_cmd_output("openstack flavor list --long")
                self.add_cmd_output("nova network-list")
                self.add_cmd_output("nova list --all-tenants")
                self.add_cmd_output("nova agent-list")
                self.add_cmd_output("nova version-list")
                self.add_cmd_output("nova hypervisor-list")
                self.add_cmd_output("openstack quota show")
                self.add_cmd_output("openstack hypervisor stats show")
                # get details for each nova instance
                cmd = "openstack server list -f value"
                nova_instances = self.exec_cmd(cmd)['output']
                for instance in nova_instances.splitlines():
                    instance = instance.split()[0]
                    cmd = "openstack server show %s" % (instance)
                    self.add_cmd_output(
                        cmd,
                        suggest_filename="instance-" + instance + ".log")

        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/nova/",
            ])
        else:
            novadir = '/var/log/nova/'
            novalogs = [
                "nova-api.log*",
                "nova-compute.log*",
                "nova-conductor.log*",
                "nova-metadata-api.log*",
                "nova-manage.log*",
                "nova-placement-api.log*",
                "nova-scheduler.log*"
            ]
            for novalog in novalogs:
                self.add_copy_spec(self.path_join(novadir, novalog))

        pp = ['', '_libvirt', '_metadata', '_placement']
        sp = [
            '/etc/nova/',
            '/etc/my.cnf.d/tripleo.cnf',
            '/etc/httpd/conf/',
            '/etc/httpd/conf.d/',
            '/etc/httpd/conf.modules.d/*.conf'
        ]
        # excludes httpd'ish specs in the libvirt path
        specs = [
            "/etc/nova/",
            "authorized_keys",
            self.var_puppet_gen + "/../memcached/etc/sysconfig/memcached",
            self.var_puppet_gen + "/var/spool/cron/nova",
            self.var_puppet_gen + "_libvirt/etc/libvirt/",
            self.var_puppet_gen + "_libvirt/etc/nova/migration/",
            self.var_puppet_gen + "_libvirt/var/lib/nova/.ssh/config"
        ] + list(
            filter(re.compile('^((?!libvirt.+httpd).)*$').match,
                   ['%s%s%s' % (
                       self.var_puppet_gen, p, s) for p in pp for s in sp
                    ]))
        self.add_copy_spec(specs)

    def apply_regex_sub(self, regexp, subst):
        self.do_path_regex_sub("/etc/nova/*", regexp, subst)
        for p in ['', '_libvirt', '_metadata', '_placement']:
            self.do_path_regex_sub(
                "%s%s/etc/nova/*" % (self.var_puppet_gen, p),
                regexp, subst)

    def postproc(self):
        protect_keys = [
            "ldap_dns_password", "neutron_admin_password", "rabbit_password",
            "qpid_password", "powervm_mgr_passwd", "virtual_power_host_pass",
            "xenapi_connection_password", "password", "host_password",
            "vnc_password", "admin_password", "connection_password",
            "memcache_secret_key", "s3_secret_key",
            "metadata_proxy_shared_secret", "fixed_key", "transport_url"
        ]
        connection_keys = ["connection", "sql_connection"]

        self.apply_regex_sub(
            r"((?m)^\s*(%s)\s*=\s*)(.*)" % "|".join(protect_keys),
            r"\1*********"
        )
        self.apply_regex_sub(
            r"((?m)^\s*(%s)\s*=\s*(.*)://(\w*):)(.*)(@(.*))" %
            "|".join(connection_keys),
            r"\1*********\6"
        )


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
    service_name = "nova-api.service"

    def setup(self):
        super(DebianNova, self).setup()
        self.add_copy_spec([
            "/etc/sudoers.d/nova_sudoers",
            "/usr/share/polkit-1/rules.d/60-libvirt.rules",
        ])


class RedHatNova(OpenStackNova, RedHatPlugin):

    nova = False
    packages = ('openstack-selinux',)

    def setup(self):
        super(RedHatNova, self).setup()
        self.add_copy_spec([
            "/etc/logrotate.d/openstack-nova",
            "/etc/polkit-1/localauthority/50-local.d/50-nova.pkla",
            "/etc/sudoers.d/nova",
            "/etc/security/limits.d/91-nova.conf",
            "/etc/sysconfig/openstack-nova-novncproxy"
        ])
        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/httpd/nova*",
                "/var/log/httpd/placement*",
            ])
        else:
            self.add_copy_spec([
                "/var/log/httpd/nova*.log",
                "/var/log/httpd/placement*.log",
            ])

# vim: set et ts=4 sw=4 :
