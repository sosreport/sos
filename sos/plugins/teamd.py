# Copyright (C) 2014 Red Hat, Inc. Bryn M. Reeves <bmr@redhat.com>
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

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
