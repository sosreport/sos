# Copyright (C) 2016 Red Hat, Inc.,Poornima M. Kshirsagar <pkshiras@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class OpenStackManila(Plugin):

    short_desc = 'OpenStack Manila'
    plugin_name = "openstack_manila"
    profiles = ('openstack', 'openstack_controller')
    containers = ('.*manila_api',)
    var_puppet_gen = "/var/lib/config-data/puppet-generated/manila"

    def setup(self):

        pre_conf = (
            self.var_puppet_gen if self.container_exists('.*manila_api') else
            '')
        config_dir = f"{pre_conf}/etc/manila"
        manila_cmd = f"manila-manage --config-dir {config_dir} db version"
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

        self.add_file_tags({
            ".*/etc/manila/manila.conf": "manila_conf"
        })

    def apply_regex_sub(self, regexp, subst):
        """ Apply regex substitution """
        self.do_path_regex_sub("/etc/manila/*", regexp, subst)
        self.do_path_regex_sub(
            self.var_puppet_gen + "/etc/manila/*",
            regexp, subst
        )

    def postproc(self):
        protect_keys = [".*password.*", "transport_url",
                        "hdfs_ssh_pw", "maprfs_ssh_pw",
                        "memcache_secret_key"]
        connection_keys = ["connection", "sql_connection"]

        join_con_keys = "|".join(connection_keys)

        self.apply_regex_sub(
            fr"(^\s*({'|'.join(protect_keys)})\s*=\s*)(.*)",
            r"\1*********"
        )
        self.apply_regex_sub(
            fr"(^\s*({join_con_keys})\s*=\s*(.*)://(\w*):)(.*)(@(.*))",
            r"\1*********\6"
        )


class DebianManila(OpenStackManila, DebianPlugin, UbuntuPlugin):

    short_desc = 'OpenStack Manila information for Debian based distributions'
    packages = (
        'python-manila',
        'manila-common',
        'manila-api',
        'manila-share',
        'manila-scheduler',
        'python3-manila',
    )

    def setup(self):
        super().setup()
        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/apache2/manila*",
            ])
        else:
            self.add_copy_spec([
                "/var/log/apache2/manila*.log",
            ])


class RedHatManila(OpenStackManila, RedHatPlugin):

    short_desc = 'OpenStack Manila information for Red Hat distributions'
    packages = ('openstack-selinux',)

    def setup(self):
        super().setup()
        self.add_copy_spec("/etc/sudoers.d/manila")

        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/containers/manila/*"
            ])
        else:
            self.add_copy_spec([
                "/var/log/containers/manila/*.log"
            ])


# vim: et ts=4 sw=4
