# Copyright (C) 2019 Mirantis, Inc., Denis Egorenko <degorenko@mirantis.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, DebianPlugin, UbuntuPlugin


class OpenStackBarbican(Plugin, DebianPlugin, UbuntuPlugin):

    short_desc = "OpenStack Barbican Secure storage service"
    plugin_name = "openstack_barbican"
    profiles = ('openstack', 'openstack_controller')

    packages = (
        'barbican-common',
        'barbican-keystone-listener',
        'barbican-worker'
    )

    requires_root = False

    def setup(self):
        self.add_copy_spec("/etc/barbican/")

        if self.get_option("all_logs"):
            self.add_copy_spec("/var/log/barbican/*")
        else:
            self.add_copy_spec("/var/log/barbican/*.log")

        self.add_forbidden_path("/etc/barbican/*.pem")
        self.add_forbidden_path("/etc/barbican/alias/*")

    def postproc(self):
        protect_keys = [
            "password", "rabbit_password", "memcache_secret_key"
        ]
        self.do_file_sub(
            "/etc/barbican/barbican.conf",
            r"((?m)^\s*(%s)\s*=\s*)(.*)" % "|".join(protect_keys),
            r"\1********"
        )

        connection_keys = ["transport_url", "sql_connection"]

        self.do_path_regex_sub(
            "/etc/barbican/barbican.conf",
            r"((?m)^\s*(%s)\s*=\s*(.*)://(\w*):)(.*)(@(.*))" %
            "|".join(connection_keys),
            r"\1*********\6")


# vim: set et ts=4 sw=4 :
