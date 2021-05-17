# Copyright (C) 2019 Red Hat, Inc., Lee Yarwood <lyarwood@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class OpenStackPlacement(Plugin):

    short_desc = 'OpenStack Placement'
    plugin_name = "openstack_placement"
    profiles = ('openstack', 'openstack_controller')

    var_puppet_gen = "/var/lib/config-data/puppet-generated/placement"
    service_name = 'openstack-placement-api'

    def setup(self):

        # collect commands output only if the openstack-placement-api service
        # is running

        in_container = self.container_exists('.*placement_api')

        if self.is_service_running(self.service_name) or in_container:
            placement_config = ""
            # if containerized we need to pass the config to the cont.
            if in_container:
                placement_config = "--config-dir " + self.var_puppet_gen + \
                                "/etc/placement/"
            self.add_cmd_output(
                "placement-manage " + placement_config + " db version",
                suggest_filename="placement-manage_db_version"
            )

        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/placement/",
                "/var/log/containers/placement/",
                "/var/log/containers/httpd/placement-api/"
            ])
        else:
            self.add_copy_spec([
                "/var/log/placement/*.log",
                "/var/log/containers/placement/*.log",
                "/var/log/containers/httpd/placement-api/*log",
            ])

        self.add_copy_spec([
            "/etc/placement/",
            self.var_puppet_gen + "/etc/placement/",
            self.var_puppet_gen + "/etc/my.cnf.d/tripleo.cnf",
            self.var_puppet_gen + "/etc/httpd/conf/",
            self.var_puppet_gen + "/etc/httpd/conf.d/",
            self.var_puppet_gen + "/etc/httpd/conf.modules.d/*.conf",
        ])

    def apply_regex_sub(self, regexp, subst):
        self.do_path_regex_sub("/etc/placement/*", regexp, subst)
        self.do_path_regex_sub(
            self.var_puppet_gen + "/etc/placement/*",
            regexp, subst
        )

    def postproc(self):
        protect_keys = ["password"]
        connection_keys = ["database_connection", "slave_connection"]

        self.apply_regex_sub(
            r"((?m)^\s*(%s)\s*=\s*)(.*)" % "|".join(protect_keys),
            r"\1*********"
        )
        self.apply_regex_sub(
            r"((?m)^\s*(%s)\s*=\s*(.*)://(\w*):)(.*)(@(.*))" %
            "|".join(connection_keys),
            r"\1*********\6"
        )


class DebianPlacement(OpenStackPlacement, DebianPlugin, UbuntuPlugin):

    packages = ('placement',)
    service_name = 'placement-api'

    def setup(self):
        super(DebianPlacement, self).setup()
        if self.get_option("all_logs"):
            self.add_copy_spec("/var/log/apache2/placement*")
        else:
            self.add_copy_spec("/var/log/apache2/placement*.log")


class RedHatPlacement(OpenStackPlacement, RedHatPlugin):

    packages = ('openstack-selinux',)

    def setup(self):
        super(RedHatPlacement, self).setup()
        if self.get_option("all_logs"):
            self.add_copy_spec("/var/log/httpd/placement*")
        else:
            self.add_copy_spec("/var/log/httpd/placement*.log")

# vim: set et ts=4 sw=4 :
