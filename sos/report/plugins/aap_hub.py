# Copyright (c) 2024 Mike Silmser <msilmser@redhat.com>
# Copyright (c) 2024 Lucas Benedito <lbenedit@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class AAPAutomationHub(Plugin, RedHatPlugin):
    short_desc = 'AAP Automation Hub plugin'
    plugin_name = 'aap_hub'
    profiles = ('sysmgmt', 'ansible',)
    packages = ('automation-hub',)

    def setup(self):
        self.add_copy_spec([
            "/etc/ansible-automation-platform/",
            "/var/log/ansible-automation-platform/hub/worker.log*",
            "/var/log/ansible-automation-platform/hub/pulpcore-api.log*",
            "/var/log/ansible-automation-platform/hub/pulpcore-content.log*",
            "/var/log/nginx/automationhub.access.log*",
            "/var/log/nginx/automationhub.error.log*",
        ])

        # systemd service status which starts with "pulpcore"
        result = self.exec_cmd(
            'systemctl list-units --type=service --no-legend pulpcore*'
        )
        if result['status'] == 0:
            for svc in result['output'].splitlines():
                pulpcore_svc = svc.split()
                if not pulpcore_svc:
                    continue
                self.add_service_status(pulpcore_svc[0])

        self.add_service_status([
                "nginx",
                "redis"
        ])

        self.add_forbidden_path([
            "/etc/ansible-automation-platform/redis/server.crt",
            "/etc/ansible-automation-platform/redis/server.key",
        ])

        self.add_dir_listing([
            "/etc/ansible-automation-platform/",
            "/var/log/ansible-automation-platform/",
        ], recursive=True)

# vim: set et ts=4 sw=4 :
