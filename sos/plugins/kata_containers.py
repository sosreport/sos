# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from sos.plugins import (Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin,
                         SuSEPlugin)


class KataContainers(Plugin, RedHatPlugin, DebianPlugin,
                     UbuntuPlugin, SuSEPlugin):
    """Kata Containers configuration
    """

    plugin_name = 'kata_containers'
    profiles = ('system', 'virt', 'container')
    packages = ('kata-runtime',)

    def setup(self):
        self.limit = self.get_option('log_size')

        if self.get_option('all_logs'):
            # no limit on amount of data recorded
            self.limit = None

        self.add_cmd_output('kata-runtime kata-env')

        config_files = set()

        # start with the default file locations
        config_files.add('/etc/kata-containers/configuration.toml')
        config_files.add(
                '/usr/share/defaults/kata-containers/configuration.toml')

        # obtain a list of config files by asking the runtime
        cmd = 'kata-runtime --kata-show-default-config-paths'
        configs = self.get_command_output(cmd)
        if configs and configs['status']:
            for config in configs['output'].splitlines():
                if config != "":
                    config_files.add(config)

            self.add_copy_spec(config_files)

        self.add_journal(identifier='kata-proxy')
        self.add_journal(identifier='kata-shim')
        self.add_journal(identifier='kata-runtime')
        self.add_journal(units='kata-ksm-throttler')

# vim: set et ts=4 sw=4 :
