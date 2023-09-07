# Copyright 2023 Red Hat, Inc. Evgeny Slutsky <eslutsky@redhat.com>
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class Greenboot(Plugin, RedHatPlugin):
    """The greenboot plugin collects systemd service logs and configuration.
    """

    short_desc = 'Greenboot'
    plugin_name = 'greenboot'
    services = (plugin_name, 'greenboot-healthcheck',
                'greenboot-task-runner', 'redboot-task-runner',)
    profiles = ('system',)

    def setup(self):
        self.add_copy_spec([
            "/etc/greenboot/greenboot.conf",
        ])
