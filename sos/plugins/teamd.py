# Copyright (C) 2014 Red Hat, Inc. Bryn M. Reeves <bmr@redhat.com>
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Teamd(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Network interface teaming
    """

    plugin_name = 'teamd'
    profiles = ('network', 'hardware', )

    packages = ('teamd',)

    def _get_team_interfaces(self):
        teams = []
        ip_result = self.get_command_output("ip -o link")
        if ip_result['status'] != 0:
            return teams
        for line in ip_result['output'].splitlines():
            fields = line.split()
            if fields[1][0:4] == 'team':
                teams.append(fields[1][:-1])
        return teams

    def setup(self):
        self.add_copy_spec([
            "/etc/dbus-1/system.d/teamd.conf",
            "/usr/lib/systemd/system/teamd@.service"
        ])
        teams = self._get_team_interfaces()
        for team in teams:
            self.add_cmd_output([
                "teamdctl %s state" % team,
                "teamdctl %s state dump" % team,
                "teamdctl %s config dump" % team,
                "teamnl %s option" % team,
                "teamnl %s ports" % team
            ])

# vim: set et ts=4 sw=4 :
