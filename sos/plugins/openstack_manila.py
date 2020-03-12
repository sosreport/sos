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

        config_dir = "%s/etc/manila" % (
            self.var_puppet_gen if self.running_in_container() else ''
        )
        manila_cmd = "manila-manage --config-dir %s db version" % config_dir
        self.add_cmd_output(manila_cmd, suggest_filename="manila_db_version")

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
            ])
        else:
            self.add_copy_spec([
                "/var/log/manila/*.log",
            ])

    def running_in_container(self):
        for runtime in ["docker", "podman"]:
            container_status = self.exec_cmd(runtime + " ps")
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
