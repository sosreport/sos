# Copyright (C) 2023 Red Hat, Inc., Roberto Alfieri <ralfieri@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class OpenStackEDPM(Plugin, RedHatPlugin):

    short_desc = 'Installation information from OpenStack EDPM deployment'

    plugin_name = 'openstack_edpm'
    profiles = ('openstack', 'openstack_edpm')
    services = ('edpm-container-shutdown',)
    edpm_log_paths = []

    def setup(self):
        # These directories are present on OpenStack EDPM nodes and are
        # collected recursively.
        self.edpm_log_paths = [
            '/etc/os-net-config/',
            '/var/lib/config-data/',
            '/var/lib/edpm-config/',
            '/var/lib/openstack/',
        ]
        self.add_copy_spec(self.edpm_log_paths)
        self.add_forbidden_path([
            "/var/lib/openstack/**/ssh-privatekey",
            "/var/lib/openstack/certs",
            "/var/lib/openstack/cacerts",
        ])

    def postproc(self):
        # Ensures we do not leak passwords from the EDPM related locations.
        regexp = r'(".*(key|password|pass|secret|database_connection))' \
                 r'([":\s]+)(.*[^"])([",]+)'
        for path in self.edpm_log_paths:
            self.do_path_regex_sub(path, regexp, r'\1\3*********\5')

        protect_keys = [
            ".*_key",
            ".*_pass(wd|word)?",
            "password",
            "metadata_proxy_shared_secret",
            "rbd_secret_uuid",
        ]
        connection_keys = ["connection", "sql_connection", "transport_url"]

        join_con_keys = "|".join(connection_keys)

        self.do_path_regex_sub(
            r"/var/lib/openstack/.*",
            fr"(^\s*({'|'.join(protect_keys)})\s*=\s*)(.*)",
            r"\1*********"
        )
        self.do_path_regex_sub(
            r"/var/lib/openstack/.*",
            fr"(^\s*({join_con_keys})\s*=\s*(.*)://(\w*):)(.*)(@(.*))",
            r"\1*********\6"
        )

# vim: set et ts=4 sw=4 :
