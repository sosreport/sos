# Copyright (C) 2009 Red Hat, Inc., Joey Boggs <jboggs@redhat.com>
# Copyright (C) 2012 Rackspace US, Inc.,
#                    Justin Shepherd <jshepher@rackspace.com>
# Copyright (C) 2013 Red Hat, Inc., Flavio Percoco <fpercoco@redhat.com>
# Copyright (C) 2013 Red Hat, Inc., Jeremy Agee <jagee@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
import os


class OpenStackCinder(Plugin):

    short_desc = 'OpenStack cinder'
    plugin_name = "openstack_cinder"
    profiles = ('openstack', 'openstack_controller')
    containers = ('.*cinder_api',)

    var_puppet_gen = "/var/lib/config-data/puppet-generated/cinder"

    def setup(self):
        self.add_forbidden_path('/etc/cinder/volumes')
        cinder_config = ""
        cinder_config_opt = "--config-dir %s/etc/cinder/"

        # check if either standalone (cinder-api) or httpd wsgi (cinder_wsgi)
        # is up and running
        cinder_process = ["cinder_wsgi", "cinder-wsgi", "cinder-api"]
        in_ps = False
        for process in cinder_process:
            in_ps = self.check_process_by_name(process)
            if in_ps:
                break

        in_container = self.container_exists('.*cinder_api')
        if in_container:
            cinder_config = cinder_config_opt % self.var_puppet_gen

        # collect commands output if the standalone, wsgi or container is up
        if in_ps or in_container:
            self.add_cmd_output(
                "cinder-manage " + cinder_config + " db version",
                suggest_filename="cinder_db_version"
            )
            self.add_cmd_output(
                f"cinder-manage {cinder_config} backup list"
            )
            self.add_cmd_output(
                f"cinder-manage {cinder_config} config list"
            )
            self.add_cmd_output(
                f"cinder-manage {cinder_config} host list"
            )
            self.add_cmd_output(
                f"cinder-status {cinder_config} upgrade check"
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
                list_cmds = [
                    "backend pool",
                    "group type",
                    "message",
                    "qos",
                    "service",
                    "type",
                ]

                for cmd in list_cmds:
                    self.add_cmd_output(f"openstack volume {cmd} list")

                list_cmds_projects = [
                    "backup",
                    "group",
                    "group snapshot",
                    "snapshot",
                    "transfer request",
                    "",
                ]

                for cmd in list_cmds_projects:
                    self.add_cmd_output(
                        f"openstack volume {cmd} list --all-projects"
                    )

                # get details for each volume
                cmd = "openstack volume list -f value --all-projects"
                res = self.exec_cmd(cmd)
                if res['status'] == 0:
                    cinder_volumes = res['output']
                    for volume in cinder_volumes.splitlines():
                        volume = volume.split()[0]
                        cmd = f"openstack volume show {volume}"
                        self.add_cmd_output(cmd)

        self.add_forbidden_path('/etc/cinder/volumes')
        self.add_copy_spec([
            "/etc/cinder/",
            self.var_puppet_gen + "/etc/cinder/",
            self.var_puppet_gen + "/etc/httpd/conf/",
            self.var_puppet_gen + "/etc/httpd/conf.d/",
            self.var_puppet_gen + "/etc/httpd/conf.modules.d/*.conf",
            self.var_puppet_gen + "/etc/my.cnf.d/tripleo.cnf",
            self.var_puppet_gen + "/etc/sysconfig/",
        ])

        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/cinder/",
                f"/var/log/{self.apachepkg}*/cinder*",
            ])
        else:
            self.add_copy_spec([
                "/var/log/cinder/*.log",
                f"/var/log/{self.apachepkg}*/cinder*.log",
            ])

    def apply_regex_sub(self, regexp, subst):
        self.do_path_regex_sub("/etc/cinder/*", regexp, subst)
        self.do_path_regex_sub(
            self.var_puppet_gen + "/etc/cinder/*",
            regexp, subst
        )

    def postproc(self):
        protect_keys = [
            "admin_password", "backup_tsm_password", "chap_password",
            "nas_password", "cisco_fc_fabric_password", "coraid_password",
            "eqlx_chap_password", "fc_fabric_password",
            "hitachi_auth_password", "hitachi_horcm_password",
            "hp3par_password", "hplefthand_password", "memcache_secret_key",
            "netapp_password", "netapp_sa_password", "nexenta_password",
            "password", "qpid_password", "rabbit_password", "san_password",
            "ssl_key_password", "vmware_host_password", "zadara_password",
            "zfssa_initiator_password", "hmac_keys", "zfssa_target_password",
            "os_privileged_user_password", "transport_url"
        ]
        connection_keys = ["connection"]

        self.apply_regex_sub(
            r"(^\s*(%s)\s*=\s*)(.*)" % "|".join(protect_keys),
            r"\1*********"
        )
        self.apply_regex_sub(
            r"(^\s*(%s)\s*=\s*(.*)://(\w*):)(.*)(@(.*))" %
            "|".join(connection_keys),
            r"\1*********\6"
        )


class DebianCinder(OpenStackCinder, DebianPlugin, UbuntuPlugin):

    cinder = False
    apachepkg = 'apache2'
    packages = (
        'cinder-api',
        'cinder-backup',
        'cinder-common',
        'cinder-scheduler',
        'cinder-volume',
        'python-cinder',
        'python3-cinder',
    )


class RedHatCinder(OpenStackCinder, RedHatPlugin):

    cinder = False
    apachepkg = 'httpd'
    packages = ('openstack-selinux',)

    def setup(self):
        super(RedHatCinder, self).setup()
        self.add_copy_spec(["/etc/sudoers.d/cinder"])


# vim: set et ts=4 sw=4 :
