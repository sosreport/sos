# Copyright (C) 2013 Louis Bouchard <louis.bouchard@ubuntu.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, UbuntuPlugin, DebianPlugin


class Apt(Plugin, DebianPlugin, UbuntuPlugin):
    """ APT - advanced packaging tool
    """

    plugin_name = 'apt'
    profiles = ('system', 'sysmgmt', 'packagemanager')

    def setup(self):
        self.add_copy_spec([
            "/etc/apt", "/var/log/apt"
        ])

        self.add_cmd_output([
            "apt-get check",
            "apt-config dump",
            "apt-cache stats",
            "apt-cache policy"
        ])
        dpkg_result = self.call_ext_prog(
            "dpkg-query -W -f='${binary:Package}\t${status}\n'")
        dpkg_output = dpkg_result['output'].splitlines()
        pkg_list = ' '.join(
            [v.split('\t')[0] for v in dpkg_output if 'ok installed' in v])
        self.add_cmd_output(
            "apt-cache policy {}".format(pkg_list),
            suggest_filename="apt-cache_policy_details"
        )

# vim: set et ts=4 sw=4 :
