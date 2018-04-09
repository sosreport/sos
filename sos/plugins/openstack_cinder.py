# Copyright (C) 2009 Red Hat, Inc., Joey Boggs <jboggs@redhat.com>
# Copyright (C) 2012 Rackspace US, Inc.,
#                    Justin Shepherd <jshepher@rackspace.com>
# Copyright (C) 2013 Red Hat, Inc., Flavio Percoco <fpercoco@redhat.com>
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


class OpenStackCinder(Plugin):
    """OpenStack cinder
    """
    plugin_name = "openstack_cinder"
    profiles = ('openstack', 'openstack_controller')

    var_puppet_gen = "/var/lib/config-data/puppet-generated/cinder"

    def setup(self):

        # check if either standalone (cinder-api) or httpd wsgi (cinder_wsgi)
        # is up and running
        cinder_process = ["cinder_wsgi", "cinder-api"]
        in_ps = False
        for process in cinder_process:
            in_ps = self.check_process_by_name(process)
            if in_ps:
                break

        container_status = self.get_command_output("docker ps")
        in_container = False
        cinder_config = ""
        if container_status['status'] == 0:
            for line in container_status['output'].splitlines():
                if line.endswith("cinder_api"):
                    in_container = True
                    # if containerized we need to pass the config to the cont.
                    cinder_config = "--config-dir " + self.var_puppet_gen + \
                                    "/etc/cinder/"
                    break

        # collect commands output if the standalone, wsgi or container is up
        if in_ps or in_container:
            self.add_cmd_output(
                "cinder-manage " + cinder_config + " db version",
                suggest_filename="cinder_db_version"
            )

        self.add_copy_spec([
            "/etc/cinder/",
            self.var_puppet_gen + "/etc/cinder/",
            self.var_puppet_gen + "/etc/httpd/conf/",
            self.var_puppet_gen + "/etc/httpd/conf.d/",
            self.var_puppet_gen + "/etc/httpd/conf.modules.d/*.conf",
            self.var_puppet_gen + "/etc/my.cnf.d/tripleo.cnf",
            self.var_puppet_gen + "/etc/sysconfig/",
        ])

        self.limit = self.get_option("log_size")
        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/cinder/",
                "/var/log/httpd/cinder*",
                "/var/log/containers/cinder/",
                "/var/log/containers/httpd/cinder-api/"
            ], sizelimit=self.limit)
        else:
            self.add_copy_spec([
                "/var/log/cinder/*.log",
                "/var/log/httpd/cinder*.log",
                "/var/log/containers/cinder/*.log",
                "/var/log/containers/httpd/cinder-api/*log"
            ], sizelimit=self.limit)

        if self.get_option("verify"):
            self.add_cmd_output("rpm -V %s" % ' '.join(self.packages))

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
            "zfssa_initiator_password", "connection", "zfssa_target_password",
            "os_privileged_user_password", "hmac_keys"
        ]

        regexp = r"((?m)^\s*(%s)\s*=\s*)(.*)" % "|".join(protect_keys)
        self.do_path_regex_sub("/etc/cinder/*", regexp, r"\1*********")
        self.do_path_regex_sub(
            self.var_puppet_gen + "/etc/cinder/*",
            regexp, r"\1*********"
        )


class DebianCinder(OpenStackCinder, DebianPlugin, UbuntuPlugin):

    cinder = False
    packages = (
        'cinder-api',
        'cinder-backup',
        'cinder-common',
        'cinder-scheduler',
        'cinder-volume',
        'python-cinder',
        'python-cinderclient'
    )

    def check_enabled(self):
        self.cinder = self.is_installed("cinder-common")
        return self.cinder

    def setup(self):
        super(DebianCinder, self).setup()


class RedHatCinder(OpenStackCinder, RedHatPlugin):

    cinder = False
    packages = ('openstack-cinder',
                'python-cinder',
                'python-cinderclient')

    def check_enabled(self):
        self.cinder = self.is_installed("openstack-cinder")
        return self.cinder

    def setup(self):
        super(RedHatCinder, self).setup()
        self.add_copy_spec(["/etc/sudoers.d/cinder"])


# vim: set et ts=4 sw=4 :
