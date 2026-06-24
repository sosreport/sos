# Copyright (C) 2026 Canonical Ltd., Ponnuvel Palaniyappa <pponnuvel@gmail.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, UbuntuPlugin


class CephNVMeoF(Plugin, RedHatPlugin, UbuntuPlugin):
    """
    This plugin collects information from Ceph NVMe-oF (NVMe over Fabrics)
    gateway nodes. NVMe-oF gateways provide block storage access over
    NVMe/TCP and are managed by cephadm as containerized daemons.

    The plugin collects gateway configuration, logs, and related
    orchestrator service information. NVMe-oF gateway support was
    introduced as a tech preview in Squid and enhanced in Tentacle (v20)
    with support for gateway groups and multiple namespaces.
    """

    short_desc = 'CEPH NVMe-oF Gateway'

    plugin_name = 'ceph_nvmeof'
    profiles = ('storage', 'container', 'ceph')
    containers = ('ceph-(.*-)?nvmeof.*',)
    files = ('/var/lib/ceph/*/nvmeof.*',)

    def setup(self):
        all_logs = self.get_option("all_logs")

        self.add_forbidden_path([
            "/etc/ceph/*keyring*",
            "/var/lib/ceph/**/*keyring*",
            # Exclude TLS/key material from NVMe-oF gateway config
            "/var/lib/ceph/**/nvmeof.*/server_cert",
            "/var/lib/ceph/**/nvmeof.*/server_key",
            "/var/lib/ceph/**/nvmeof.*/client_cert",
            "/var/lib/ceph/**/nvmeof.*/client_key",
            "/var/lib/ceph/**/nvmeof.*/root_ca_cert",
            "/var/lib/ceph/**/nvmeof.*/encryption_key",
            "/etc/ceph/*bindpass*",
        ])

        if not all_logs:
            self.add_copy_spec([
                "/var/log/ceph/**/ceph-nvmeof*.log",
            ])
        else:
            self.add_copy_spec([
                "/var/log/ceph/**/ceph-nvmeof*.log*",
            ])

        self.add_copy_spec([
            "/var/lib/ceph/**/nvmeof.*/ceph-nvmeof.conf",
        ])

# vim: set et ts=4 sw=4 :
