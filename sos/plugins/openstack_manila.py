# Copyright (C) 2016 Red Hat, Inc.,Poornima M. Kshirsagar <pkshiras@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class OpenStackManila(Plugin):
    """OpenStack Manila
    """
    plugin_name = "openstack_manila"
    profiles = ('openstack', 'openstack_controller')
    option_list = []

    var_puppet_gen = "/var/lib/config-data/puppet-generated/manila"

    def setup(self):
        manila_config_opt = "--config-dir %s/etc/manila/"

        # check eventlet-based service on the baremetal
        in_ps = self.check_process_by_name("manila-api")

        # check if manila-api is running inside a container
        # (doesn't matter if running via httpd or as a eventlet based service)
        in_container = self.running_in_container()

        if in_container:
            manila_config = manila_config_opt % self.var_puppet_gen
        else:
            manila_config = manila_config_opt % ''

        # gather DB version
        if in_ps or in_container:
            self.add_cmd_output(
                "manila-manage " + manila_config + " db version",
                suggest_filename="manila_db_version"
            )

        self.add_copy_spec([
            "/etc/manila/",
            self.var_puppet_gen + "/etc/manila/",
            self.var_puppet_gen + "/etc/my.cnf.d/tripleo.cnf",
            self.var_puppet_gen + "/etc/httpd/conf/",
            self.var_puppet_gen + "/etc/httpd/conf.d/",
            self.var_puppet_gen + "/etc/httpd/conf.modules.d/*.conf",
        ])

        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/manila/*",
                "/var/log/containers/manila/*",
                "/var/log/containers/httpd/manila-api/*"
            ])
        else:
            self.add_copy_spec([
                "/var/log/manila/*.log",
                "/var/log/containers/manila/*.log",
                "/var/log/containers/httpd/manila-api/*log"
            ])

        if self.get_option("verify"):
            self.add_cmd_output("rpm -V %s" % ' '.join(self.packages))

    def running_in_container(self):
        for runtime in ["docker", "podman"]:
            container_status = self.get_command_output(runtime + " ps")
            if container_status['status'] == 0:
                for line in container_status['output'].splitlines():
                    if line.endswith("manila_api"):
                        return True
        return False

    def apply_regex_sub(self, regexp, subst):
        self.do_path_regex_sub("/etc/manila/*", regexp, subst)
        self.do_path_regex_sub(
            self.var_puppet_gen + "/etc/manila/*",
            regexp, subst
        )

    def postproc(self):
        protect_keys = [".*password.*", "transport_url",
                        "hdfs_ssh_pw", "maprfs_ssh_pw"]
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


class DebianManila(OpenStackManila, DebianPlugin, UbuntuPlugin):
    """OpenStackManila related information for Debian based distributions."""

    packages = (
        'python-manila',
        'manila-common',
        'manila-api',
        'manila-share',
        'manila-scheduler'
    )


class RedHatManila(OpenStackManila, RedHatPlugin):
    """OpenStackManila related information for Red Hat distributions."""

    packages = ('openstack-selinux',)

    def setup(self):
        super(RedHatManila, self).setup()
        self.add_copy_spec("/etc/sudoers.d/manila")


# vim: et ts=4 sw=4
