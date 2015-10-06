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

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class OpenStackCinder(Plugin):
    """OpenStack cinder
    """
    plugin_name = "openstack_cinder"
    profiles = ('openstack', 'openstack_controller')

    option_list = [("db", "gathers openstack cinder db version", "slow",
                    False)]

    def setup(self):
        if self.get_option("db"):
            self.add_cmd_output(
                "cinder-manage db version",
                suggest_filename="cinder_db_version")

        self.add_copy_spec(["/etc/cinder/"])

        self.limit = self.get_option("log_size")
        if self.get_option("all_logs"):
            self.add_copy_spec_limit("/var/log/cinder/",
                                     sizelimit=self.limit)
        else:
            self.add_copy_spec_limit("/var/log/cinder/*.log",
                                     sizelimit=self.limit)

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
